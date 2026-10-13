"""Contract tests for the opt-in vertical inspection slice."""
from pathlib import Path

import pytest

from mcm_solarcheck.services.vertical_pipeline_contracts import (
    ReviewRequiredError, ReviewedDecision, VerticalPipelinePorts, VerticalProject,
)
from mcm_solarcheck.services.vertical_inspection_pipeline import VerticalInspectionPipeline


def ports(events, *, approved=True):
    def importer(path):
        events.append("import")
        return {"pairs": 2}

    def analyzer(imported):
        events.append("analyze")
        assert imported["pairs"] == 2
        return {"suggestions": []}

    def reviewer(analysis):
        events.append("review")
        return ReviewedDecision("reviewer", approved, "review-001")

    def reporter(analysis, review):
        events.append("report")
        return {"reviewer": review.reviewer_id, "findings": analysis["suggestions"]}

    return VerticalPipelinePorts(importer, analyzer, reviewer, reporter)


def test_complete_vertical_slice_with_explicit_review(tmp_path):
    events = []
    project = VerticalProject("customer", "project", tmp_path)
    result = VerticalInspectionPipeline(ports(events), project_authorized=lambda c, p: True).run(project)
    assert events == ["import", "analyze", "review", "report"]
    assert result.report == {"reviewer": "reviewer", "findings": []}


def test_rejected_review_never_builds_report(tmp_path):
    events = []
    pipeline = VerticalInspectionPipeline(ports(events, approved=False), project_authorized=lambda c, p: True)
    with pytest.raises(ReviewRequiredError):
        pipeline.run(VerticalProject("customer", "project", tmp_path))
    assert events == ["import", "analyze", "review"]


def test_unauthorized_project_never_touches_pipeline(tmp_path):
    events = []
    pipeline = VerticalInspectionPipeline(ports(events), project_authorized=lambda c, p: False)
    with pytest.raises(PermissionError):
        pipeline.run(VerticalProject("customer", "project", tmp_path))
    assert events == []


def test_missing_directory_fails_before_import(tmp_path):
    events = []
    pipeline = VerticalInspectionPipeline(ports(events), project_authorized=lambda c, p: True)
    with pytest.raises(ValueError):
        pipeline.run(VerticalProject("customer", "project", tmp_path / "missing"))
    assert events == []


def test_malformed_review_is_fail_closed(tmp_path):
    events = []
    p = ports(events)
    broken = VerticalPipelinePorts(p.import_project, p.analyze_project, lambda a: True, p.build_report)
    with pytest.raises(ReviewRequiredError):
        VerticalInspectionPipeline(broken, project_authorized=lambda c, p: True).run(
            VerticalProject("customer", "project", tmp_path)
        )
    assert "report" not in events
