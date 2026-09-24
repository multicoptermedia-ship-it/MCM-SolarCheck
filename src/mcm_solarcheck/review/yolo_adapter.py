"""YOLO output adapter for Phase 7.

This module has no Ultralytics dependency. It translates already-produced YOLO
detections into MCM-SolarCheck advisory evidence, keeping inference optional.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .classification import DefectClassification
from .defect_classes import DatasetClassMap, DefectClass


@dataclass(frozen=True)
class YoloDetection:
    class_name: str
    confidence: float
    box_xyxy: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if not self.class_name.strip():
            raise ValueError("YOLO class name must not be empty")
        if not isfinite(float(self.confidence)) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("YOLO confidence must be finite and between 0 and 1")
        if self.box_xyxy is not None:
            x1,y1,x2,y2=self.box_xyxy
            if not all(isfinite(float(v)) for v in self.box_xyxy) or x2 <= x1 or y2 <= y1:
                raise ValueError("YOLO box must be finite with positive area")


@dataclass(frozen=True)
class YoloAdapter:
    provider: str
    model_version: str
    class_map: DatasetClassMap
    modality: str

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("YOLO provider must not be empty")
        if not self.model_version.strip():
            raise ValueError("YOLO model version must not be empty")
        if self.modality not in {"thermal", "rgb"}:
            raise ValueError("YOLO modality must be thermal or rgb")

    def adapt(self, detection: YoloDetection) -> DefectClassification:
        canonical=self.class_map.normalize(detection.class_name)
        return DefectClassification(
            canonical.value,
            detection.confidence,
            self.provider.strip(),
            self.model_version.strip(),
            self.modality,
        )

    def select_best(self, detections: tuple[YoloDetection, ...]) -> YoloDetection | None:
        """Select the strongest defect detection; normal/unknown are not defects."""
        defects=[
            d for d in detections
            if self.class_map.normalize(d.class_name)
            not in {DefectClass.UNKNOWN, DefectClass.NORMAL}
        ]
        if not defects:
            return None
        return sorted(defects,key=lambda d:(-d.confidence,d.class_name.casefold()))[0]

    def adapt_best(self, detections: tuple[YoloDetection, ...]) -> DefectClassification | None:
        """Return deterministic highest-confidence defect suggestion."""
        best=self.select_best(detections)
        return None if best is None else self.adapt(best)
