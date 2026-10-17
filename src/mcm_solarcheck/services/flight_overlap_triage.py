"""Conservative image-link triage, separate from metric roof reconstruction."""
from __future__ import annotations
from dataclasses import dataclass

from mcm_solarcheck.services.flight_overlap_audit import FlightOverlapAudit, ImageTransition


@dataclass(frozen=True)
class TransitionConcern:
    modality: str
    first_id: str
    second_id: str
    inliers: int
    occupied_cells: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class OverlapTriage:
    concerns: tuple[TransitionConcern, ...]
    rgb_transitions: int
    thermal_transitions: int

    @property
    def requires_manual_review(self) -> bool:
        return bool(self.concerns)

    @property
    def metric_orthophoto_approved(self) -> bool:
        return False


def triage_flight_overlap(audit: FlightOverlapAudit, *, minimum_inliers=10, minimum_cells=4) -> OverlapTriage:
    """Flag weak links for review; no claim about surveyed roof or image accuracy."""
    if not isinstance(audit, FlightOverlapAudit):
        raise TypeError("FlightOverlapAudit required")
    if type(minimum_inliers) is not int or minimum_inliers < 4:
        raise ValueError("minimum_inliers must be >= 4")
    if type(minimum_cells) is not int or not 1 <= minimum_cells <= 16:
        raise ValueError("minimum_cells must be between 1 and 16")
    concerns = []
    for mode, transitions in (("RGB", audit.rgb), ("Thermal", audit.thermal)):
        for transition in transitions:
            if not isinstance(transition, ImageTransition):
                raise TypeError("ImageTransition required")
            if transition.inliers < 0 or not 0 <= transition.occupied_inlier_cells <= 16:
                raise ValueError("invalid transition evidence")
            reasons = []
            if transition.inliers < minimum_inliers:
                reasons.append("few verified matches")
            if transition.occupied_inlier_cells < minimum_cells:
                reasons.append("spatially clustered or missing matches")
            if reasons:
                concerns.append(TransitionConcern(
                    mode, transition.first_id, transition.second_id,
                    transition.inliers, transition.occupied_inlier_cells, tuple(reasons),
                ))
    return OverlapTriage(tuple(concerns), len(audit.rgb), len(audit.thermal))
