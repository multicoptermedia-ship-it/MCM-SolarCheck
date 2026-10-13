"""Fail-closed preflight for orthomosaic worker handoff."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.orthomosaic_input_validation import (
    ManualCameraAngle, OverlapAssessment, OverlapState,
)


@dataclass(frozen=True)
class OrthomosaicPreflight:
    image_count: int
    overlap: OverlapAssessment
    camera_pose_available: bool
    manual_angle: ManualCameraAngle | None = None

    def __post_init__(self) -> None:
        if self.image_count < 2:
            raise ValueError("at least two images required")
        if not isinstance(self.overlap, OverlapAssessment):
            raise TypeError("overlap assessment required")

    @property
    def can_attempt_reconstruction(self) -> bool:
        return self.overlap.reconstruction_allowed and (
            self.camera_pose_available or self.manual_angle is not None
        )

    @property
    def user_message(self) -> str:
        if self.overlap.state != OverlapState.SUFFICIENT:
            return self.overlap.user_message
        if not self.camera_pose_available and self.manual_angle is None:
            return "Bitte Kamerawinkel in Bezug zum Solarmodul eingeben."
        return "Eingaben geprüft. Die Orthofoto-Berechnung kann versucht werden."
