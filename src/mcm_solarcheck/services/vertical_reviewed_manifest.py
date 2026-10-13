"""Review-evidence manifest for the vertical pipeline; NOT a customer PDF/ODT."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
from mcm_solarcheck.services.vertical_pipeline_contracts import ReviewRequiredError, ReviewedDecision


@dataclass(frozen=True)
class InspectionEvidenceManifest:
    source: str
    paired_frames: int
    imported_thermal_frames: int
    candidate_count: int
    reviewer_id: str
    review_evidence_reference: str
    status: str = "reviewed_manifest_not_exported_report"


def build_reviewed_evidence_manifest(
    analysis: object, review: ReviewedDecision
) -> InspectionEvidenceManifest:
    if not isinstance(analysis, ImportedCandidateAnalysis):
        raise TypeError("imported analysis required")
    if not isinstance(review, ReviewedDecision) or review.approved is not True:
        raise ReviewRequiredError("expert approval required")
    return InspectionEvidenceManifest(
        source=analysis.source,
        paired_frames=analysis.paired_frames,
        imported_thermal_frames=analysis.imported_thermal_frames,
        candidate_count=len(analysis.candidates),
        reviewer_id=review.reviewer_id,
        review_evidence_reference=review.evidence_reference,
    )
