"""Read-only inspection of local YOLO detection label/image pairs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.services.pv_dataset_intake import ImageModality, PublicDatasetRecord
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping
from mcm_solarcheck.services.pv_yolo_dataset_validation import parse_yolo_detection_labels


@dataclass(frozen=True)
class LocalYoloInspection:
    inspected_pairs: int
    annotation_count: int
    unmapped_annotations: int
    training_allowed: bool


def inspect_local_yolo_dataset(
    root: Path,
    record: PublicDatasetRecord,
    mapping: YoloClassMapping,
    *,
    max_pairs: int = 1000,
    max_label_bytes: int = 65536,
) -> LocalYoloInspection:
    if not isinstance(record, PublicDatasetRecord) or not isinstance(mapping, YoloClassMapping):
        raise TypeError("dataset record and class mapping required")
    if record.modality is not mapping.modality:
        raise ValueError("dataset and mapping modalities differ")
    if type(max_pairs) is not int or not 1 <= max_pairs <= 100000:
        raise ValueError("invalid file count limit")
    if type(max_label_bytes) is not int or not 1 <= max_label_bytes <= 1048576:
        raise ValueError("invalid label size limit")
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("local dataset directory required, without symlink")
    labels = root / "labels"
    images = root / "images"
    if labels.is_symlink() or images.is_symlink() or not labels.is_dir() or not images.is_dir():
        raise ValueError("labels and images directories required")
    entries = list(labels.iterdir())
    if len(entries) > max_pairs:
        raise ValueError("dataset exceeds inspection limit")
    if any(entry.is_symlink() or not entry.is_file() or entry.suffix.lower() != ".txt" for entry in entries):
        raise ValueError("only regular YOLO label files accepted")
    total = unmapped = 0
    for label in sorted(entries):
        matches = [images / (label.stem + extension) for extension in (".jpg", ".jpeg", ".png")]
        matches = [path for path in matches if path.exists()]
        if len(matches) != 1 or not matches[0].is_file() or matches[0].is_symlink():
            raise ValueError("exactly one regular matching image required")
        if label.stat().st_size > max_label_bytes:
            raise ValueError("label file too large")
        detections = parse_yolo_detection_labels(label.read_text(encoding="utf-8"),
                                                  len(mapping.external_names))
        total += len(detections)
        unmapped += sum(mapping.observation_for_class(item.class_id) is None for item in detections)
    return LocalYoloInspection(len(entries), total, unmapped,
                               record.can_train_commercially(mapping.modality) and unmapped == 0)
