"""Prepare, never export, RGB training candidates from expert-reviewed thermal leads."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.pv_ai_fault_taxonomy import ObservationKind


@dataclass(frozen=True)
class RGBTrainingCandidate:
    thermal_finding_id: str
    rgb_frame_id: str
    registration_reference: str
    rgb_observation: ObservationKind | None
    bbox_xyxy: tuple[float, float, float, float] | None
    reviewer_id: str
    training_consent_active: bool
    consent_reference: str | None
    status: str = "pending_quality_review"

    def __post_init__(self) -> None:
        if not all((self.thermal_finding_id.strip(), self.rgb_frame_id.strip(),
                    self.registration_reference.strip(), self.reviewer_id.strip())):
            raise ValueError("finding, frame, registration and reviewer evidence required")
        if self.rgb_observation is not None and not self.rgb_observation.value.startswith("rgb_"):
            raise ValueError("RGB training labels must be optically observable")
        if (self.rgb_observation is None) != (self.bbox_xyxy is None):
            raise ValueError("visible RGB finding and bounding box must be provided together")
        if self.bbox_xyxy is not None:
            x1, y1, x2, y2 = self.bbox_xyxy
            from math import isfinite
            if not all(isfinite(v) for v in self.bbox_xyxy) or not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
                raise ValueError("normalized bounding box must be within image")
        if self.training_consent_active and not self.consent_reference:
            raise ValueError("active training consent needs auditable reference")

    @property
    def eligible_for_training_review(self) -> bool:
        return (self.training_consent_active and bool(self.consent_reference)
                and self.rgb_observation is not None and self.bbox_xyxy is not None
                and self.status == "pending_quality_review")
