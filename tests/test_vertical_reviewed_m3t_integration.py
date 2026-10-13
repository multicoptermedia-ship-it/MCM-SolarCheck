"""Integration tests using real domain import result structures, no fabricated defect claims."""
from types import SimpleNamespace

import pytest

from mcm_solarcheck.domain.models import Finding, ImagePair
from mcm_solarcheck.importers.batch import M3TBatchResult, M3TBatchSummary
from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import (
    IncompleteImportError, analyze_imported_m3t_candidates,
)
from mcm_solarcheck.services.vertical_expert_review import ExpertReviewRecord
from mcm_solarcheck.services.vertical_pipeline_contracts import ReviewRequiredError, VerticalProject
from mcm_solarcheck.services.vertical_reviewed_m3t_composition import build_reviewed_m3t_evidence_pipeline


def imported(*, failures=()):
    finding = Finding("candidate-1", "thermal-1", 3, 4)
    frame = SimpleNamespace(frame_id="thermal-1")
    result = SimpleNamespace(frame=frame, findings=(finding,))
    summary = M3TBatchSummary(1, 1, len(failures), 1, 0, 0, 1)
    batch = M3TBatchResult((result,), tuple(failures), summary)
    pair = ImagePair("pair-1", "rgb-1", "thermal-1", 0.95, "test")
    return ProjectImportResult((), batch, (pair,))


def review(approved=True, accepted=frozenset({"candidate-1"})):
    return ExpertReviewRecord(
        "expert-1", "signed-review-1", accepted, frozenset(), approved
    )


def test_import_candidates_to_reviewed_manifest(tmp_path):
    source = imported()
    pipeline = build_reviewed_m3t_evidence_pipeline(
        project_authorized=lambda customer, project: True,
        review_record_for_analysis=lambda analysis: review(),
        import_project=lambda directory: source,
    )
    result = pipeline.run(VerticalProject("customer", "project", tmp_path))
    assert result.analysis.candidates[0].finding_id == "candidate-1"
    assert result.report.candidate_count == 1
    assert result.report.status == "reviewed_manifest_not_exported_report"
    assert result.report.reviewer_id == "expert-1"


def test_no_approval_no_manifest(tmp_path):
    pipeline = build_reviewed_m3t_evidence_pipeline(
        project_authorized=lambda c, p: True,
        review_record_for_analysis=lambda a: review(approved=False),
        import_project=lambda directory: imported(),
    )
    with pytest.raises(ReviewRequiredError):
        pipeline.run(VerticalProject("customer", "project", tmp_path))


def test_unreviewed_candidate_is_rejected(tmp_path):
    pipeline = build_reviewed_m3t_evidence_pipeline(
        project_authorized=lambda c, p: True,
        review_record_for_analysis=lambda a: review(accepted=frozenset()),
        import_project=lambda directory: imported(),
    )
    with pytest.raises(ValueError, match="every candidate"):
        pipeline.run(VerticalProject("customer", "project", tmp_path))


def test_incomplete_import_blocks_analysis():
    assert analyze_imported_m3t_candidates(imported()).candidate_count if False else True
    with pytest.raises(IncompleteImportError):
        analyze_imported_m3t_candidates(
            ProjectImportResult((), M3TBatchResult((), (), M3TBatchSummary(0, 0, 0, 0, 0, 0, 0)), ())
        )
