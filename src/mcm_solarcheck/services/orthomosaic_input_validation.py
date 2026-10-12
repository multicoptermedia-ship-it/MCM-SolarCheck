"""Explicit manual incidence and measured overlap outcomes for reconstruction gates."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class OverlapState(str, Enum):
    UNKNOWN = "unknown"
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"


OVERLAP_FAILURE_MESSAGE = "Keine Berechnung möglich, da die Bildüberlappung fehlerhaft ist."


@dataclass(frozen=True)
class ManualCameraAngle:
    """Acute angle between viewing ray and module plane, 90° is normal."""
    angle_to_module_deg: float
    scope: str
    source: str = "user_supplied"

    def __post_init__(self) -> None:
        if not isfinite(self.angle_to_module_deg) or not 0 <= self.angle_to_module_deg <= 90:
            raise ValueError("camera-to-module angle must be finite and between 0 and 90 degrees")
        if self.scope not in ("series", "image"):
            raise ValueError("angle scope must be series or image")
        if self.source != "user_supplied":
            raise ValueError("manual angle provenance required")


@dataclass(frozen=True)
class OverlapAssessment:
    state: OverlapState
    method: str | None = None
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        if self.state != OverlapState.UNKNOWN and (
            not self.method or not self.method.strip()
            or not self.evidence_reference or not self.evidence_reference.strip()
        ):
            raise ValueError("measured overlap result needs method and evidence")
        if self.state == OverlapState.UNKNOWN and (self.method or self.evidence_reference):
            raise ValueError("unknown overlap cannot carry a claimed measurement")

    @property
    def reconstruction_allowed(self) -> bool:
        return self.state == OverlapState.SUFFICIENT

    @property
    def user_message(self) -> str:
        if self.state == OverlapState.INSUFFICIENT:
            return OVERLAP_FAILURE_MESSAGE
        if self.state == OverlapState.UNKNOWN:
            return "Bildüberlappung wurde noch nicht geprüft."
        return "Bildüberlappung geprüft."
