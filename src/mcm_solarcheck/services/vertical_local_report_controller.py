"""Local-only controller linking review draft, report model and guarded export."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from mcm_solarcheck.services.vertical_local_review_draft import LocalReviewDraft
from mcm_solarcheck.services.vertical_report_adapter import ReportContext, build_reviewed_inspection_report
from mcm_solarcheck.services.vertical_report_export import export_reviewed_inspection
from mcm_solarcheck.services.vertical_review_snapshot import snapshot_expert_review


class LocalReviewedReportController:
    def __init__(self, draft: LocalReviewDraft, context: ReportContext):
        if not isinstance(draft, LocalReviewDraft) or not isinstance(context, ReportContext):
            raise TypeError("review draft and report context required")
        self._draft = draft
        self._context = context
        self._report = None
        self._approved_decisions = None
        self._approved_analysis = None
        self._approved_corrections = None

    def approve(self, *, reviewer_id: str, evidence_reference: str):
        record = self._draft.finalize(
            reviewer_id=reviewer_id, evidence_reference=evidence_reference, approve_report=True
        )
        snapshot = snapshot_expert_review(self._draft.analysis, record)
        self._report = build_reviewed_inspection_report(self._draft.analysis, snapshot, self._context)
        self._approved_decisions = dict(self._draft.decisions)
        self._approved_analysis = self._draft.analysis
        self._approved_corrections = dict(self._draft.corrections)
        return self._report

    def export(self, destination: str | Path, *, authorize_export: Callable[[str], bool]):
        if self._report is None:
            raise PermissionError("report has not been approved")
        if (self._draft.remaining or self._draft.decisions != self._approved_decisions
                or self._draft.analysis != self._approved_analysis
                or self._draft.corrections != self._approved_corrections):
            raise PermissionError("review changed after approval; new approval required")
        return export_reviewed_inspection(self._report, destination, authorize_export=authorize_export)
