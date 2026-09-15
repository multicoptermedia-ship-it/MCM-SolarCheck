"""Create reviewable inspection findings from thermal anomaly candidates."""

from __future__ import annotations

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from .analysis import RawAnomalyCandidate


def candidate_to_finding(
    candidate: RawAnomalyCandidate,
    frame: ThermalFrame,
    *,
    rank: int,
) -> Finding:
    """Attach frame-level geospatial evidence to a raw thermal candidate.

    Pixel-to-ground projection is intentionally not guessed here. Until camera
    intrinsics/pose projection is validated, the frame GPS position is retained
    as evidence and labelled as frame-level rather than candidate-level GPS.
    """
    return Finding(
        finding_id=f"{frame.frame_id}:raw:{rank:04d}",
        thermal_frame_id=frame.frame_id,
        pixel_x=candidate.x,
        pixel_y=candidate.y,
        raw_value=candidate.raw_value,
        raw_delta_from_median=candidate.delta_from_median,
        position=frame.position,
        rtk=frame.rtk,
        metadata={
            "coordinate_scope": "frame",
            "temperature_status": "uncalibrated_raw",
            "candidate_threshold_raw": str(candidate.percentile_threshold),
        },
    )


def candidates_to_findings(
    candidates: tuple[RawAnomalyCandidate, ...],
    frame: ThermalFrame,
) -> tuple[Finding, ...]:
    return tuple(
        candidate_to_finding(candidate, frame, rank=index)
        for index, candidate in enumerate(candidates, start=1)
    )
