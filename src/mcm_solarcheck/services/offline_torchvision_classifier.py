"""Optional CPU-only PyTorch + TorchVision local classification trainer.

No remote hubs, automatic weight downloads, commercial SDKs, GPU requirements
or online model registry. This is an experimental model-training adapter, not
a validated PV fault-detection system. PyTorch/torchvision are OPTIONAL imports.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
import math
import os
from pathlib import Path

from mcm_solarcheck.services.offline_ai_open_source import (
    LOCAL_BACKEND, LocalCheckpointProvenance, digest_file,
    encode_provenance, manifest_path, verify_local_checkpoint,
)
from mcm_solarcheck.services.offline_training_preflight import (
    OfflineTrainerConfiguration, VerifiedOfflineDataset,
    verify_staged_classification_dataset,
)
from mcm_solarcheck.services.offline_training_jobs import TrainingCancelled


def _libraries():
    """Lazy import: the normal desktop needs neither torch nor torchvision."""
    try:
        import torch
        from torchvision import models, transforms
        import torchvision
    except ImportError as exc:
        raise RuntimeError(
            "optional locally installed PyTorch and TorchVision are required"
        ) from exc
    return torch, torchvision, models, transforms


def initialize_local_resnet18(
    destination: Path, *, classes: int, seed: int,
) -> LocalCheckpointProvenance:
    """Explicitly create fresh random weights on this machine, never download.

    The operator supplies an empty absolute destination. A locally created
    manifest is evidence of file integrity but no cryptographic attestation.
    """
    location = manifest_path(destination)
    if (destination.exists() or destination.is_symlink()
            or location.exists() or location.is_symlink()):
        raise FileExistsError("local model or provenance already exists")
    if destination.parent.is_symlink() or not destination.parent.is_dir():
        raise ValueError("model destination must have an existing real parent")
    # Validate arguments before importing the large optional dependencies.
    if type(classes) is not int or not 2 <= classes <= 100:
        raise ValueError("2-100 classification classes required")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("invalid model initialization seed")
    torch, torchvision, models, _transforms = _libraries()
    torch.manual_seed(seed)
    # Passing weights=None is critical: no ImageNet/other pretrained download.
    model = models.resnet18(weights=None, num_classes=classes)
    created = False
    try:
        with destination.open("xb") as file:
            created = True
            torch.save(model.state_dict(), file)
            file.flush()
            os.fsync(file.fileno())
        provenance = LocalCheckpointProvenance(
            digest_file(destination), str(torch.__version__),
            str(torchvision.__version__), classes, seed,
        )
        with location.open("xb") as file:
            file.write(encode_provenance(provenance))
            file.flush()
            os.fsync(file.fileno())
        return provenance
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        # Never delete a preexisting manifest created by a concurrent operator.
        raise


def local_resnet18_trainer(
    dataset: VerifiedOfflineDataset,
    config: OfflineTrainerConfiguration,
    output: Path,
    progress,
    cancelled,
) -> Path:
    """Train local images by class, evaluate holdout, return UNDEPLOYED weights.

    Requires an explicitly provisioned model and a trusted pre-existing
    offline training consent. Does not infer diagnoses or train segmentation.
    """
    if not isinstance(dataset, VerifiedOfflineDataset):
        raise TypeError("verified dataset required")
    if not isinstance(config, OfflineTrainerConfiguration) or config.backend != LOCAL_BACKEND:
        raise PermissionError("explicit local TorchVision backend required")
    if config.task != "classification" or config.epochs > 30:
        raise PermissionError("only bounded offline classification training allowed")
    if not callable(progress) or not hasattr(cancelled, "is_set"):
        raise ValueError("cooperative progress/cancellation required")
    if output.is_symlink() or not output.is_dir() or not output.is_absolute():
        raise PermissionError("private existing local output directory required")
    if cancelled.is_set():
        raise TrainingCancelled()
    config.verify_model()
    fresh = verify_staged_classification_dataset(dataset.folder)
    if fresh.fingerprint != dataset.fingerprint or fresh.classes != dataset.classes:
        raise PermissionError("reviewed training data changed before backend launch")
    evidence = verify_local_checkpoint(
        config.model_weights, expected_sha256=config.model_sha256,
        class_count=len(dataset.classes),
    )
    if config.weights_license_review != "local-init-no-external-pretrained-weights":
        raise PermissionError("only locally initialized weights accepted by OSS adapter")
    torch, torchvision, models, transforms = _libraries()
    if (str(torch.__version__) != evidence.torch_version
            or str(torchvision.__version__) != evidence.torchvision_version
            or config.backend_version != evidence.torchvision_version):
        raise PermissionError("installed framework differs from checkpoint provenance")
    rows = json.loads((dataset.folder / "training-index.json").read_text(encoding="utf-8"))["samples"]
    modalities = {row["modality"] for row in rows}
    if len(modalities) != 1:
        raise PermissionError("do not mix RGB and thermal representations in one classifier")
    classes = dataset.classes
    by_split = {
        split: [row for row in rows if row["split"] == split]
        for split in ("train", "validation", "test")
    }
    if len(by_split["train"]) < 2 or any(not by_split[k] for k in ("validation", "test")):
        raise PermissionError("at least two training images and independent held-out splits required")
    torch.manual_seed(config.seed)
    transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.ToTensor(),
    ])
    class_to_index = {name: index for index, name in enumerate(classes)}

    class LocalImages(torch.utils.data.Dataset):
        def __init__(self, records):
            self.records = records

        def __len__(self):
            return len(self.records)

        def __getitem__(self, index):
            from PIL import Image
            record = self.records[index]
            if cancelled.is_set():
                raise TrainingCancelled()
            path = dataset.folder / record["image"]
            if path.is_symlink() or not path.is_file():
                raise PermissionError("training image missing or linked")
            raw = path.read_bytes()
            if len(raw) > 25_000_000 or sha256(raw).hexdigest() != record["sha256"]:
                raise PermissionError("training image content changed")
            with Image.open(BytesIO(raw)) as image:
                if image.width * image.height > 20_000_000 or min(image.size) < 2:
                    raise ValueError("unsafe image dimensions")
                normalized = image.convert("RGB")
                value = transform(normalized)
            return value, class_to_index[record["defect_class"]]

    loaders = {
        name: torch.utils.data.DataLoader(
            LocalImages(by_split[name]),
            batch_size=2, shuffle=name == "train",
            num_workers=0, drop_last=name == "train",
            generator=torch.Generator().manual_seed(config.seed),
        )
        for name in by_split
    }
    model = models.resnet18(weights=None, num_classes=len(classes))
    # Load tensor data only; never unpickle a general Python object.
    state = torch.load(config.model_weights, map_location="cpu", weights_only=True)
    if not isinstance(state, dict):
        raise PermissionError("state_dict-only local checkpoint required")
    model.load_state_dict(state, strict=True)
    model.to("cpu")
    optimizer = torch.optim.SGD(model.parameters(), lr=0.005, momentum=0.9)
    loss_fn = torch.nn.CrossEntropyLoss()

    def evaluate(name):
        if cancelled.is_set():
            raise TrainingCancelled()
        model.eval()
        good = total = 0
        with torch.no_grad():
            for images, target in loaders[name]:
                if cancelled.is_set():
                    raise TrainingCancelled()
                predicted = model(images).argmax(dim=1)
                good += int((predicted == target).sum().item())
                total += int(target.shape[0])
        return good / total if total else 0.0

    final_loss = None
    validation_accuracy = None
    for epoch in range(config.epochs):
        if cancelled.is_set():
            raise TrainingCancelled()
        model.train()
        loss_sum = batches = 0
        for images, target in loaders["train"]:
            if cancelled.is_set():
                raise TrainingCancelled()
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(images), target)
            if not math.isfinite(float(loss.detach().item())):
                raise ValueError("non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            loss_sum += float(loss.detach().item())
            batches += 1
        if not batches:
            raise ValueError("train split lacks a usable batch")
        final_loss = loss_sum / batches
        validation_accuracy = evaluate("validation")
        progress(min(95, int(95 * (epoch + 1) / config.epochs)))
    if cancelled.is_set():
        raise TrainingCancelled()
    test_accuracy = evaluate("test")
    progress(98)
    if cancelled.is_set():
        raise TrainingCancelled()
    checkpoint = output / "resnet18-experimental.pt"
    metadata = output / "training-metrics.json"
    if checkpoint.exists() or metadata.exists():
        raise FileExistsError("never overwrite existing model weights or metrics")
    with checkpoint.open("xb") as file:
        torch.save(model.state_dict(), file)
        file.flush()
        os.fsync(file.fileno())
    metrics = {
        "status": "experimental_not_deployed",
        "task": "classification",
        "backend": LOCAL_BACKEND,
        "architecture": "torchvision.resnet18",
        "dataset_id": dataset.dataset_id,
        "dataset_fingerprint": dataset.fingerprint,
        "input_weights_sha256": evidence.weights_sha256,
        "output_weights_sha256": digest_file(checkpoint),
        "classes": list(classes),
        "modality": next(iter(modalities)),
        "counts": {split: len(by_split[split]) for split in by_split},
        "epochs": config.epochs,
        "seed": config.seed,
        "training_loss": final_loss,
        "validation_accuracy": validation_accuracy,
        "heldout_test_accuracy": test_accuracy,
        "evaluation_limit": "experimental sample metrics; not validated PV fault performance",
    }
    with metadata.open("x", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2, sort_keys=True)
        file.write("\n")
    if cancelled.is_set():
        raise TrainingCancelled()
    return checkpoint
