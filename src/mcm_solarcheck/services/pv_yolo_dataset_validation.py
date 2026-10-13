"""Validate local YOLO detection labels without loading images or training models."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import PurePosixPath


@dataclass(frozen=True)
class YoloDetection:
    class_id: int
    center_x: float
    center_y: float
    width: float
    height: float


def parse_yolo_detection_labels(text: str, class_count: int) -> tuple[YoloDetection, ...]:
    if type(class_count) is not int or class_count < 1:
        raise ValueError("nonempty class vocabulary required")
    result: list[YoloDetection] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"line {line_number}: expected YOLO class and four coordinates")
        try:
            class_id = int(fields[0])
            values = tuple(float(value) for value in fields[1:])
        except ValueError as exc:
            raise ValueError(f"line {line_number}: invalid YOLO numeric value") from exc
        x, y, w, h = values
        if not (0 <= class_id < class_count and all(isfinite(v) for v in values)
                and 0 < w <= 1 and 0 < h <= 1 and w / 2 <= x <= 1 - w / 2
                and h / 2 <= y <= 1 - h / 2):
            raise ValueError(f"line {line_number}: class or bounding box outside image")
        result.append(YoloDetection(class_id, x, y, w, h))
    return tuple(result)


def validate_group_splits(groups: dict[str, set[str]]) -> None:
    """Require non-overlapping flight/site groups across train/val/test."""
    if set(groups) != {"train", "val", "test"}:
        raise ValueError("train, val and test groups required")
    if any(not value for value in groups.values()):
        raise ValueError("each split needs at least one site or flight")
    if (groups["train"] & groups["val"] or groups["train"] & groups["test"]
            or groups["val"] & groups["test"]):
        raise ValueError("site/flight leakage across splits")


def validate_dataset_relative_path(path: str) -> str:
    normalized = PurePosixPath(path)
    if not path or path.startswith(("/", "\\")) or "\\" in path or ".." in normalized.parts or normalized.is_absolute():
        raise ValueError("unsafe dataset path")
    return str(normalized)
