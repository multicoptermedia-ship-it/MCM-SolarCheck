"""In-memory local expert review draft; no implicit decisions or network writes."""
from __future__ import annotations

from dataclasses import dataclass, field

from mcm_solarcheck.services.vertical_expert_review import ExpertReviewRecord
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
from mcm_solarcheck.services.vertical_review_view import candidate_review_rows


@dataclass
class LocalReviewDraft:
    analysis: ImportedCandidateAnalysis
    decisions: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self._ids = frozenset(row.finding_id for row in candidate_review_rows(self.analysis))
        if self.decisions:
            raise ValueError("review draft must start without decisions")

    def decide(self, finding_id: str, status: str) -> None:
        if finding_id not in self._ids:
            raise KeyError("candidate does not belong to this analysis")
        if status not in ("accept", "reject"):
            raise ValueError("status must be accept or reject")
        self.decisions[finding_id] = status

    @property
    def remaining(self) -> int:
        return len(self._ids - self.decisions.keys())

    def finalize(self, *, reviewer_id: str, evidence_reference: str, approve_report: bool) -> ExpertReviewRecord:
        if self.remaining:
            raise ValueError("all candidates require an explicit decision")
        if type(approve_report) is not bool:
            raise TypeError("approve_report must be boolean")
        return ExpertReviewRecord(
            reviewer_id=reviewer_id,
            evidence_reference=evidence_reference,
            accepted_finding_ids=frozenset(k for k, v in self.decisions.items() if v == "accept"),
            rejected_finding_ids=frozenset(k for k, v in self.decisions.items() if v == "reject"),
            approve_report=approve_report,
        )
