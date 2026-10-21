"""Offline-only, fail-closed preflight for an explicitly configured AI trainer.

The existing report training index contains classification labels, NOT YOLO
boxes, segmentation polygons, radiometric targets or validated PV diagnoses.
Only a separate, explicitly installed and reviewed classification backend may
consume these samples. No model is supplied or auto-downloaded by SolarCheck.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

_HEX64 = re.compile(r"[a-f0-9]{64}\Z")
_IMAGE = re.compile(r"sample-[0-9]{5}\.(?:jpg|jpeg|png|tif|tiff)\Z")


@dataclass(frozen=True)
class OfflineTrainerConfiguration:
    backend: str
    backend_version: str
    model_weights: Path
    model_sha256: str
    weights_license_review: str
    epochs: int
    seed: int
    task: str = "classification"

    def __post_init__(self) -> None:
        if self.task != "classification":
            raise ValueError("this staged index is classification-only; no YOLO geometry")
        if any(not isinstance(v, str) or not v.strip() or len(v) > 200
               for v in (self.backend, self.backend_version, self.weights_license_review)):
            raise ValueError("trained model backend and license review required")
        if not isinstance(self.model_sha256, str) or not _HEX64.fullmatch(self.model_sha256):
            raise ValueError("model SHA-256 required")
        if type(self.epochs) is not int or not 1 <= self.epochs <= 500:
            raise ValueError("reviewed epoch count required")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("reviewed seed required")
        if not isinstance(self.model_weights, Path) or not self.model_weights.is_absolute():
            raise ValueError("absolute model source required")

    def verify_model(self) -> None:
        if (self.model_weights.is_symlink() or not self.model_weights.is_file()
                or self.model_weights.suffix.lower() != ".pt"):
            raise PermissionError("regular local PyTorch model checkpoint required")
        if not 0 < self.model_weights.stat().st_size <= 500_000_000:
            raise ValueError("model checkpoint size out of bounds")
        if _sha256(self.model_weights) != self.model_sha256:
            raise PermissionError("model source no longer matches approved SHA-256")


@dataclass(frozen=True)
class VerifiedOfflineDataset:
    folder: Path
    sample_count: int
    dataset_id: str
    classes: tuple[str, ...]
    splits: tuple[str, ...]
    fingerprint: str


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_staged_classification_dataset(
    folder: Path, *, max_images: int = 1500, min_samples: int = 6,
) -> VerifiedOfflineDataset:
    """Rehash every private file; enforce disjoint groups and all three splits."""
    if not isinstance(folder, Path) or not folder.is_absolute():
        raise ValueError("absolute local dataset folder required")
    if folder.is_symlink() or not folder.is_dir():
        raise PermissionError("private training directory is missing or linked")
    manifest_path = folder / "training-index.json"
    if (manifest_path.is_symlink() or not manifest_path.is_file()
            or not 0 < manifest_path.stat().st_size <= 1_000_000):
        raise PermissionError("private training manifest unavailable")
    try:
        raw = manifest_path.read_bytes()
        record = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("training manifest invalid") from exc
    if not isinstance(record, dict) or set(record) != {"dataset_id", "samples"}:
        raise ValueError("training manifest has unexpected fields")
    if not isinstance(record["dataset_id"], str) or not _HEX64.fullmatch(record["dataset_id"]):
        raise ValueError("invalid dataset identity")
    samples = record["samples"]
    if not isinstance(samples, list) or not min_samples <= len(samples) <= max_images:
        raise PermissionError("minimum six reviewed, rights-approved samples required")
    files = {item.name for item in folder.iterdir()}
    if files != {"training-index.json"} | {x.get("image") for x in samples if isinstance(x, dict)}:
        raise PermissionError("training directory contains unexpected or missing files")
    groups: dict[str, str] = {}
    classes: set[str] = set()
    splits: set[str] = set()
    seen: set[str] = set()
    fingerprint = hashlib.sha256(raw)
    for item in samples:
        if not isinstance(item, dict) or set(item) != {
            "image", "sha256", "modality", "defect_class", "split", "inspection_group_key",
        }:
            raise ValueError("incomplete reviewed training row")
        name, digest, group = item["image"], item["sha256"], item["inspection_group_key"]
        if (not isinstance(name, str) or not _IMAGE.fullmatch(name) or name in seen
                or not isinstance(digest, str) or not _HEX64.fullmatch(digest)
                or not isinstance(group, str) or not _HEX64.fullmatch(group)):
            raise PermissionError("training row identity or content hash invalid")
        if item["modality"] not in ("rgb", "thermal"):
            raise ValueError("unsupported training modality")
        label, split = item["defect_class"], item["split"]
        if (not isinstance(label, str) or not label.strip() or label == "unknown"
                or not isinstance(split, str) or split not in ("train", "validation", "test")):
            raise ValueError("invalid reviewed training label or split")
        prior = groups.setdefault(group, split)
        if prior != split:
            raise PermissionError("physical inspection group leaked across splits")
        path = folder / name
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 25_000_000:
            raise PermissionError("training sample unavailable or linked")
        if _sha256(path) != digest:
            raise PermissionError("local training image hash differs from approval")
        seen.add(name)
        classes.add(label)
        splits.add(split)
        fingerprint.update(bytes.fromhex(digest))
    if len(classes) < 2 or splits != {"train", "validation", "test"}:
        raise PermissionError("training requires >=2 reviewed classes and disjoint train/validation/test")
    return VerifiedOfflineDataset(
        folder, len(samples), record["dataset_id"],
        tuple(sorted(classes)), tuple(sorted(splits)), fingerprint.hexdigest(),
    )
