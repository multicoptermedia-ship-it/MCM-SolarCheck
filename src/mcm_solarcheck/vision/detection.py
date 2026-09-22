"""Normalize external/AI PV-module detections into SolarCheck domain objects."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.domain.models import PVModule


@dataclass(frozen=True)
class ModuleDetection:
    polygon_px: tuple[tuple[float, float], ...]
    confidence: float
    class_name: str = "pv_module"

    def __post_init__(self) -> None:
        if len(self.polygon_px) < 3:
            raise ValueError("Detection polygon requires at least three points")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Detection confidence must be between 0 and 1")


def normalize_module_detections(
    frame_id: str,
    detections: tuple[ModuleDetection, ...],
    *,
    detector_name: str,
    minimum_confidence: float = 0.50,
    image_size: tuple[int, int] | None = None,
    validate_geometry: bool = True,
) -> tuple[PVModule, ...]:
    """Filter and deterministically number detector output.

    This adapter deliberately accepts already-computed detections. It therefore
    keeps YOLO/segmentation frameworks outside the domain layer and makes model
    replacement straightforward.
    """
    if not 0.0 <= minimum_confidence <= 1.0:\n        raise ValueError("minimum_confidence must be between 0 and 1")\n    accepted = tuple(d for d in detections if d.class_name == "pv_module" and d.confidence >= minimum_confidence)\n    if validate_geometry:\n        if image_size is None:\n            raise ValueError("image_size is required when geometry validation is enabled")\n        from mcm_solarcheck.vision.module_quality import filter_module_detections\n        accepted = filter_module_detections(accepted, image_size[0], image_size[1])\n    accepted = list(accepted)\n    accepted.sort(key=lambda d: (min(y for _, y in d.polygon_px), min(x for x, _ in d.polygon_px), -d.confidence))
    return tuple(
        PVModule(
            module_id=f"{frame_id}:M-{index:04d}", frame_id=frame_id,
            polygon_px=detection.polygon_px, detection_confidence=detection.confidence,
            detector=detector_name,
            metadata={"source_class": detection.class_name},
        )
        for index, detection in enumerate(accepted, start=1)
    )
