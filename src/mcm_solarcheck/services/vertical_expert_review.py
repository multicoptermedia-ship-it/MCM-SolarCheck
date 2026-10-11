"""Explicit expert review of imported anomaly candidates, never automatic approval."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
from mcm_solarcheck.services.vertical_pipeline_contracts import ReviewedDecision


@dataclass(frozen=True)
class ExpertReviewRecord:
    reviewer_id: str
    evidence_reference: str
    accepted_finding_ids: frozenset[str]
    rejected_finding_ids: frozenset[str]
    approve_report: bool

    def __post_init__(self):
        if not self.reviewer_id.strip() or not self.evidence_reference.strip():
            raise ValueError("reviewer identity and evidence required")
        if type(self.approve_report) is not bool:
            raise TypeError("approve_report must be boolean")


def review_imported_candidates(
    analysis: object, record: ExpertReviewRecord
) -> ReviewedDecision:
    if not isinstance(analysis, ImportedCandidateAnalysis):
        raise TypeError("imported candidate analysis required")
    if not isinstance(record, ExpertReviewRecord):
        raise TypeError("explicit expert review required")
    ids = [finding.finding_id for finding in analysis.candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate candidate IDs require manual resolution")
    accepted, rejected = record.accepted_finding_ids, record.rejected_finding_ids
    if accepted & rejected or accepted | rejected != set(ids):
        raise ValueError("every candidate must have exactly one explicit decision")
    return ReviewedDecision(
        reviewer_id=record.reviewer_id,
        approved=record.approve_report,
        evidence_reference=record.evidence_reference,
    )
