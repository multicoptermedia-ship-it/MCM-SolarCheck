"""Separate visible PV anomalies from electrical fault hypotheses."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ObservationKind(str, Enum):
    THERMAL_HOTSPOT = "thermal_hotspot"
    THERMAL_SUBSTRING_PATTERN = "thermal_substring_pattern"
    RGB_GLASS_DAMAGE = "rgb_glass_damage"
    RGB_SOILING = "rgb_soiling"
    RGB_SHADING = "rgb_shading"
    RGB_DISCOLORATION = "rgb_discoloration"
    RGB_CELL_FRACTURE_VISIBLE = "rgb_cell_fracture_visible"


class FaultHypothesis(str, Enum):
    OPEN_INTERCONNECT_OR_SUBSTRING = "open_interconnect_or_substring"
    INSULATION_FAULT = "insulation_fault"
    STRING_INTERRUPTION = "string_interruption"
    CELL_FRACTURE = "cell_fracture"
    BYPASS_DIODE_SHORT = "bypass_diode_short"
    BYPASS_DIODE_OPEN = "bypass_diode_open"
    PID = "potential_induced_degradation"


@dataclass(frozen=True)
class PVFaultAssessment:
    observation: ObservationKind
    possible_causes: tuple[FaultHypothesis, ...]
    evidence_reference: str
    review_status: str = "suspected"

    def __post_init__(self) -> None:
        if not isinstance(self.observation, ObservationKind):
            raise ValueError("known observable signature required")
        if not self.evidence_reference.strip():
            raise ValueError("evidence reference required")
        if self.review_status not in ("suspected", "expert_reviewed"):
            raise ValueError("unsupported review status")
        if any(not isinstance(cause, FaultHypothesis) for cause in self.possible_causes):
            raise ValueError("unknown electrical hypothesis")
        if len(set(self.possible_causes)) != len(self.possible_causes):
            raise ValueError("duplicate electrical hypotheses")

    @property
    def requires_followup(self) -> bool:
        return bool(self.possible_causes)
