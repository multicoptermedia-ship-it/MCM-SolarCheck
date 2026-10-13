"""Block 38.4: explicit expert correction must precede AI report release."""
from datetime import datetime, timezone

import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.services.vertical_local_review_draft import LocalReviewDraft
from mcm_solarcheck.services.vertical_local_report_controller import LocalReviewedReportController
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
from mcm_solarcheck.services.vertical_report_adapter import ReportContext


def _setup():
    analysis = ImportedCandidateAnalysis(1, 1, (
        Finding("ai-1", "thermal-1", 12, 14,
                finding_type="local_ai_suggestion_unverified", module_id="module-1"),
    ))
    draft = LocalReviewDraft(analysis)
    context = ReportContext(
        "report-1", "project-1", "Customer", "PV Site",
        datetime(2026, 10, 13, tzinfo=timezone.utc), "expert", 10, "test-version",
    )
    return draft, LocalReviewedReportController(draft, context)


def test_accepting_unverified_ai_cannot_approve_report():
    draft, controller = _setup()
    draft.decide("ai-1", "accept")
    with pytest.raises(ValueError, match="expert-verified finding label"):
        controller.approve(reviewer_id="expert", evidence_reference="signed")


def test_explicit_correction_requires_new_decision_and_approval():
    draft, controller = _setup()
    draft.decide("ai-1", "accept")
    draft.correct_ai_finding("ai-1", "Fachlich bestätigter Hotspot")
    assert draft.remaining == 1
    assert draft.analysis.candidates[0].finding_type == "Fachlich bestätigter Hotspot"
    with pytest.raises(ValueError, match="explicit decision"):
        controller.approve(reviewer_id="expert", evidence_reference="signed")
    draft.decide("ai-1", "accept")
    report = controller.approve(reviewer_id="expert", evidence_reference="signed")
    assert report.details[0].finding_label == "Fachlich bestätigter Hotspot"


@pytest.mark.parametrize("label", ["", "  ", "local_ai_suggestion_unverified", None])
def test_invalid_expert_labels_rejected(label):
    draft, _ = _setup()
    with pytest.raises(ValueError):
        draft.correct_ai_finding("ai-1", label)


def test_unknown_candidate_cannot_be_corrected():
    draft, _ = _setup()
    with pytest.raises(KeyError):
        draft.correct_ai_finding("unknown", "Hotspot")


def test_post_approval_correction_invalidates_export(tmp_path):
    draft, controller = _setup()
    draft.correct_ai_finding('ai-1', 'Hotspot')
    draft.decide('ai-1', 'accept')
    controller.approve(reviewer_id='expert', evidence_reference='signed')
    draft.correct_ai_finding('ai-1', 'Thermische Auffaelligkeit')
    draft.decide('ai-1', 'accept')
    with pytest.raises(PermissionError, match='review changed'):
        controller.export(tmp_path / 'stale.pdf', authorize_export=lambda _: True)
    assert not (tmp_path / 'stale.pdf').exists()
