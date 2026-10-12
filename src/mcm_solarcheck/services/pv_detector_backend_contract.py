"""Backend-neutral detection result contracts; no model imports or inference."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from mcm_solarcheck.services.pv_detector_license_gate import (
    DetectorFamily, DetectorLicenseReview, require_proprietary_detector_license,
)


@dataclass(frozen=True)
class DetectionBox:
    class_index: int
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        if type(self.class_index) is not int or self.class_index < 0:
            raise ValueError("invalid class index")
        values = (self.confidence, self.x_min, self.y_min, self.x_max, self.y_max)
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not isfinite(v) for v in values):
            raise ValueError("finite detection coordinates required")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence out of range")
        if not (0 <= self.x_min < self.x_max <= 1 and 0 <= self.y_min < self.y_max <= 1):
            raise ValueError("normalized box outside image")


@dataclass(frozen=True)
class DetectorManifest:
    family: DetectorFamily
    model_reference: str
    classes: tuple[str, ...]
    license_evidence_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.family, DetectorFamily) or not self.model_reference.strip():
            raise ValueError("valid model identity required")
        if not self.classes or any(not c.strip() for c in self.classes) or len(set(self.classes)) != len(self.classes):
            raise ValueError("unique class names required")
        if not self.license_evidence_reference.strip():
            raise ValueError("license evidence required")


def require_licensed_detector_manifest(manifest: DetectorManifest, review: DetectorLicenseReview) -> None:
    if not isinstance(manifest, DetectorManifest):
        raise PermissionError("detector manifest required")
    require_proprietary_detector_license(review)
    if manifest.family is not review.family or manifest.license_evidence_reference != review.evidence_reference:
        raise PermissionError("detector manifest and license review mismatch")
