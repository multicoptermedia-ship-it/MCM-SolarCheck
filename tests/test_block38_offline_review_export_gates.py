"""Block 38.2: offline-first review and export safety regression tests.

These tests use the shared vertical report core; online adapters must obey
the same explicit expert-review and export-authorization gates.
"""
from datetime import datetime, timezone

import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.services.vertical_local_review_draft import LocalReviewDraft
from mcm_solarcheck.services.vertical_local_report_controller import LocalReviewedReportController
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
from mcm_solarcheck.services.vertical_report_adapter import ReportContext


def _controller():
    analysis = ImportedCandidateAnalysis(
        1, 1, (Finding("candidate-1", "thermal-1", 12, 15, module_id="module-1"),)
    )
    draft = LocalReviewDraft(analysis)
    context = ReportContext(
        "report-38", "project-38", "Customer", "PV Site",
        datetime(2026, 10, 13, tzinfo=timezone.utc),
        "expert", 10, "test-version",
    )
    return draft, LocalReviewedReportController(draft, context)


def test_pending_candidate_cannot_be_approved_or_exported(tmp_path):
    draft, controller = _controller()
    assert draft.remaining == 1
    with pytest.raises(ValueError, match="explicit decision"):
        controller.approve(reviewer_id="expert", evidence_reference="signed-38")
    with pytest.raises(PermissionError, match="not been approved"):
        controller.export(tmp_path / "blocked.pdf", authorize_export=lambda _: True)
    assert not (tmp_path / "blocked.pdf").exists()


def test_rejected_candidate_requires_explicit_report_approval(tmp_path):
    draft, controller = _controller()
    draft.decide("candidate-1", "reject")
    with pytest.raises(PermissionError):
        controller.export(tmp_path / "blocked.pdf", authorize_export=lambda _: True)
    assert not (tmp_path / "blocked.pdf").exists()


def test_review_change_invalidates_prior_approval(tmp_path):
    draft, controller = _controller()
    draft.decide("candidate-1", "accept")
    controller.approve(reviewer_id="expert", evidence_reference="signed-38")
    draft.decide("candidate-1", "reject")
    with pytest.raises(PermissionError, match="review changed"):
        controller.export(tmp_path / "stale.pdf", authorize_export=lambda _: True)
    assert not (tmp_path / "stale.pdf").exists()


def test_export_requires_separate_authorization(tmp_path):
    draft, controller = _controller()
    draft.decide("candidate-1", "accept")
    controller.approve(reviewer_id="expert", evidence_reference="signed-38")
    with pytest.raises(PermissionError):
        controller.export(tmp_path / "denied.pdf", authorize_export=lambda _: False)
    assert not (tmp_path / "denied.pdf").exists()
