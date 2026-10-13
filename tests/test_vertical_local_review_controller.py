"""Local review interaction tests with real report/export adapters."""
from datetime import datetime, timezone

import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.services.vertical_local_review_draft import LocalReviewDraft
from mcm_solarcheck.services.vertical_local_report_controller import LocalReviewedReportController
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
from mcm_solarcheck.services.vertical_report_adapter import ReportContext
from mcm_solarcheck.services.vertical_review_view import candidate_review_rows


def setup():
    analysis = ImportedCandidateAnalysis(
        1, 1, (Finding("finding-1", "thermal-1", 12, 15, module_id="module-1"),)
    )
    draft = LocalReviewDraft(analysis)
    context = ReportContext(
        "report-1", "project-1", "Customer", "PV Site",
        datetime(2026, 10, 11, tzinfo=timezone.utc), "expert", 10, "test-version"
    )
    return analysis, draft, LocalReviewedReportController(draft, context)


def test_review_rows_are_unconfirmed():
    analysis, _, _ = setup()
    rows = candidate_review_rows(analysis)
    assert rows[0].finding_id == "finding-1"
    assert rows[0].proposed_type == "thermal_anomaly_candidate"


def test_every_candidate_requires_manual_decision():
    _, draft, controller = setup()
    assert draft.remaining == 1
    with pytest.raises(ValueError):
        controller.approve(reviewer_id="expert", evidence_reference="signed-1")
    with pytest.raises(KeyError):
        draft.decide("unknown", "accept")
    with pytest.raises(ValueError):
        draft.decide("finding-1", "maybe")
    draft.decide("finding-1", "accept")
    assert draft.remaining == 0


def test_local_approved_report_exports_pdf(tmp_path):
    _, draft, controller = setup()
    draft.decide("finding-1", "accept")
    report = controller.approve(reviewer_id="expert", evidence_reference="signed-1")
    assert report.conspicuous_modules == 1
    path = controller.export(tmp_path / "inspection.pdf", authorize_export=lambda project: True)
    assert path.is_file() and path.stat().st_size > 0


def test_no_export_before_approval(tmp_path):
    _, draft, controller = setup()
    draft.decide("finding-1", "reject")
    with pytest.raises(PermissionError):
        controller.export(tmp_path / "blocked.pdf", authorize_export=lambda project: True)


def test_wrong_inspector_does_not_approve():
    _, draft, controller = setup()
    draft.decide("finding-1", "accept")
    with pytest.raises(PermissionError):
        controller.approve(reviewer_id="different", evidence_reference="signed-1")
