"""Presentation-safe candidate rows for a future shared inspection UI."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis


@dataclass(frozen=True)
class ReviewCandidateRow:
    finding_id: str
    thermal_frame_id: str
    pixel_x: int
    pixel_y: int
    proposed_type: str
    module_id: str | None


def candidate_review_rows(analysis: ImportedCandidateAnalysis) -> tuple[ReviewCandidateRow, ...]:
    if not isinstance(analysis, ImportedCandidateAnalysis):
        raise TypeError("imported M3T analysis required")
    ids = [f.finding_id for f in analysis.candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate candidate identifiers")
    return tuple(
        ReviewCandidateRow(
            finding_id=f.finding_id,
            thermal_frame_id=f.thermal_frame_id,
            pixel_x=f.pixel_x,
            pixel_y=f.pixel_y,
            proposed_type=f.finding_type,
            module_id=f.module_id,
        )
        for f in analysis.candidates
    )
