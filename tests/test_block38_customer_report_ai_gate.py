"""Regression: AI suggestions must not leak unverified labels into customer reports."""
from datetime import datetime, timezone

import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.services.vertical_expert_review import ExpertReviewRecord
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
from mcm_solarcheck.services.vertical_report_adapter import ReportContext, build_reviewed_inspection_report
from mcm_solarcheck.services.vertical_review_snapshot import snapshot_expert_review


def _report(finding_type):
    analysis = ImportedCandidateAnalysis(1, 1, (
        Finding("ai-1", "thermal-1", 12, 14, finding_type=finding_type,
                module_id="module-1"),
    ))
    review = ExpertReviewRecord(
        reviewer_id="expert", evidence_reference="signed-review",
        accepted_finding_ids=frozenset({"ai-1"}),
        rejected_finding_ids=frozenset(),
        approve_report=True,
    )
    context = ReportContext(
        "report-1", "project-1", "Customer", "Site",
        datetime(2026, 10, 13, tzinfo=timezone.utc),
        "expert", 10, "test-version",
    )
    return build_reviewed_inspection_report(
        analysis, snapshot_expert_review(analysis, review), context
    )


def test_unverified_ai_label_is_not_customer_reportable():
    with pytest.raises(ValueError, match="expert-verified finding label"):
        _report("local_ai_suggestion_unverified")


def test_expert_verified_label_can_be_reported():
    report = _report("thermal_anomaly_candidate")
    assert report.conspicuous_modules == 1
    assert report.details[0].review_status == "confirmed"
