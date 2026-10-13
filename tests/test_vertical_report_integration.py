"""Real report-model and renderer integration with strict expert review."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.services.vertical_expert_review import ExpertReviewRecord
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
from mcm_solarcheck.services.vertical_review_snapshot import snapshot_expert_review
from mcm_solarcheck.services.vertical_report_adapter import ReportContext, build_reviewed_inspection_report
from mcm_solarcheck.services.vertical_report_export import export_reviewed_inspection
from mcm_solarcheck.services.vertical_pipeline_contracts import ReviewRequiredError


def evidence(module="module-7"):
    return ImportedCandidateAnalysis(
        1, 1, (Finding("candidate-1", "thermal-1", 2, 3,
                       finding_type="thermal_anomaly_candidate", module_id=module),)
    )


def decision(*, accepted=True, approved=True):
    return ExpertReviewRecord(
        "expert-1", "review-ref-1",
        frozenset({"candidate-1"}) if accepted else frozenset(),
        frozenset() if accepted else frozenset({"candidate-1"}),
        approved,
    )


def context():
    return ReportContext(
        "report-1", "project-1", "Example Customer", "Example PV Site",
        datetime(2026, 10, 11, tzinfo=timezone.utc), "expert-1", 10, "test-version",
    )


def report(analysis=None, record=None):
    analysis = analysis or evidence()
    snapshot = snapshot_expert_review(analysis, record or decision())
    return build_reviewed_inspection_report(analysis, snapshot, context())


def test_accepted_candidate_enters_existing_report_model():
    result = report()
    assert result.release_status == "reviewed"
    assert result.conspicuous_modules == 1
    assert result.details[0].module_id == "module-7"
    assert result.details[0].thermal_measurement is None


def test_rejected_candidate_is_not_presented_as_defect():
    result = report(record=decision(accepted=False))
    assert result.conspicuous_modules == 0
    assert result.details == ()


def test_missing_module_assignment_fails_closed():
    with pytest.raises(ValueError, match="module assignment"):
        report(analysis=evidence(module=None))


def test_unapproved_review_fails_closed():
    with pytest.raises(ReviewRequiredError):
        report(record=decision(approved=False))


def test_report_requires_matching_reviewer_and_real_module_count():
    analysis = evidence()
    snapshot = snapshot_expert_review(analysis, decision())
    with pytest.raises(PermissionError):
        build_reviewed_inspection_report(analysis, snapshot, replace(context(), inspector="other"))
    with pytest.raises(ValueError):
        build_reviewed_inspection_report(analysis, snapshot, replace(context(), total_modules=0))


def test_export_requires_reviewed_status_and_authorization(tmp_path):
    target = tmp_path / "blocked.docx"
    with pytest.raises(PermissionError):
        export_reviewed_inspection(report(), target, authorize_export=lambda p: False)
    assert not target.exists()
    with pytest.raises(ReviewRequiredError):
        export_reviewed_inspection(replace(report(), release_status="draft"), target,
                                   authorize_export=lambda p: True)
    assert not target.exists()


@pytest.mark.parametrize("format", ["docx", "odt", "pdf"])
def test_reviewed_report_exports_using_existing_renderer(tmp_path, format):
    target = tmp_path / ("inspection." + format)
    result = export_reviewed_inspection(
        report(), target, authorize_export=lambda project_id: project_id == "project-1",
    )
    assert result == target
    assert target.is_file()
    assert target.stat().st_size > 0
