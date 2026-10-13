"""Immutable expert decision snapshot for the report adapter."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.vertical_expert_review import ExpertReviewRecord, review_imported_candidates
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
from mcm_solarcheck.services.vertical_pipeline_contracts import ReviewedDecision, ReviewRequiredError


@dataclass(frozen=True)
class ApprovedCandidateSnapshot:
    decision: ReviewedDecision
    accepted_ids: frozenset[str]
    rejected_ids: frozenset[str]
    candidate_ids: frozenset[str]


def snapshot_expert_review(
    analysis: ImportedCandidateAnalysis, record: ExpertReviewRecord
) -> ApprovedCandidateSnapshot:
    decision = review_imported_candidates(analysis, record)
    if not decision.approved:
        raise ReviewRequiredError("explicit expert approval required")
    ids = frozenset(f.finding_id for f in analysis.candidates)
    return ApprovedCandidateSnapshot(
        decision, frozenset(record.accepted_finding_ids),
        frozenset(record.rejected_finding_ids), ids,
    )


def verify_review_snapshot(
    analysis: ImportedCandidateAnalysis, snapshot: ApprovedCandidateSnapshot
) -> None:
    if not isinstance(snapshot, ApprovedCandidateSnapshot):
        raise ReviewRequiredError("expert review snapshot required")
    if not isinstance(snapshot.decision, ReviewedDecision) or snapshot.decision.approved is not True:
        raise ReviewRequiredError("expert approval required")
    ids = [f.finding_id for f in analysis.candidates]
    if len(ids) != len(set(ids)) or frozenset(ids) != snapshot.candidate_ids:
        raise ReviewRequiredError("review snapshot does not match analysis")
    if (snapshot.accepted_ids & snapshot.rejected_ids or
            snapshot.accepted_ids | snapshot.rejected_ids != snapshot.candidate_ids):
        raise ReviewRequiredError("incomplete expert review snapshot")
