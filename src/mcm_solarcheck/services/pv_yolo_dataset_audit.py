"""Audit local YOLO images/labels and explicit site-disjoint splits."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.services.pv_dataset_intake import PublicDatasetRecord
from mcm_solarcheck.services.pv_training_image_quality import inspect_training_image
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping
from mcm_solarcheck.services.pv_yolo_dataset_validation import (
    parse_yolo_detection_labels, validate_group_splits,
)


@dataclass(frozen=True)
class DatasetAudit:
    images: int
    annotations: int
    negative_images: int
    training_ready: bool


def audit_local_yolo_dataset(
    root: Path, record: PublicDatasetRecord, mapping: YoloClassMapping,
    site_by_image: dict[str, str], *,
    max_images: int = 1000, max_label_bytes: int = 65536,
    max_image_bytes: int = 30_000_000,
) -> DatasetAudit:
    """Require images/{train,val,test} and labels/{train,val,test} folders."""
    if not isinstance(record, PublicDatasetRecord) or not isinstance(mapping, YoloClassMapping):
        raise TypeError("dataset record and mapping required")
    if record.modality is not mapping.modality:
        raise ValueError("modality mismatch")
    if type(max_images) is not int or not 1 <= max_images <= 100000:
        raise ValueError("invalid image limit")
    if type(max_label_bytes) is not int or not 1 <= max_label_bytes <= 1048576:
        raise ValueError("invalid label limit")
    if type(max_image_bytes) is not int or not 1 <= max_image_bytes <= 100000000:
        raise ValueError("invalid image byte limit")
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("regular dataset directory required")
    splits = ("train", "val", "test")
    groups: dict[str, set[str]] = {}
    count = annotations = negatives = unmapped = 0
    seen_names: set[str] = set()
    for split in splits:
        images_dir, labels_dir = root / "images" / split, root / "labels" / split
        if any(p.is_symlink() or not p.is_dir() for p in (images_dir, labels_dir)):
            raise ValueError("split image and label directories required")
        image_files = list(images_dir.iterdir())
        label_files = list(labels_dir.iterdir())
        if count + len(image_files) > max_images or len(label_files) > max_images:
            raise ValueError("file count limit exceeded")
        if any(p.is_symlink() or not p.is_file() or p.suffix.lower() not in (".jpg", ".jpeg", ".png") for p in image_files):
            raise ValueError("invalid image directory entry")
        if any(p.is_symlink() or not p.is_file() or p.suffix.lower() != ".txt" for p in label_files):
            raise ValueError("invalid label directory entry")
        images = {p.stem: p for p in image_files}
        labels = {p.stem: p for p in label_files}
        if len(images) != len(image_files) or len(labels) != len(label_files) or images.keys() != labels.keys():
            raise ValueError("images and annotations must match one-to-one")
        groups[split] = set()
        for stem, image_path in images.items():
            key = split + "/" + image_path.name
            if key in seen_names:
                raise ValueError("duplicate image identifier")
            seen_names.add(key)
            site = site_by_image.get(key)
            if not isinstance(site, str) or not site.strip():
                raise ValueError("explicit site or flight group required for each image")
            groups[split].add(site)
            inspect_training_image(image_path, max_file_bytes=max_image_bytes)
            label = labels[stem]
            if label.stat().st_size > max_label_bytes:
                raise ValueError("label exceeds byte limit")
            detections = parse_yolo_detection_labels(label.read_text(encoding="utf-8"), len(mapping.external_names))
            count += 1
            annotations += len(detections)
            negatives += not bool(detections)
            unmapped += sum(mapping.observation_for_class(d.class_id) is None for d in detections)
    if set(site_by_image) != seen_names:
        raise ValueError("group manifest must match all images exactly")
    validate_group_splits(groups)
    return DatasetAudit(count, annotations, negatives,
                        record.can_train_commercially(mapping.modality) and unmapped == 0)
