"""Opt-in, fail-closed end-to-end orchestration; never invents PV findings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from mcm_solarcheck.services.vertical_pipeline_contracts import (
    ReviewRequiredError, ReviewedDecision, VerticalPipelinePorts, VerticalProject,
)


@dataclass(frozen=True)
class VerticalPipelineResult:
    project: VerticalProject
    imported: object
    analysis: object
    review: ReviewedDecision
    report: object


class VerticalInspectionPipeline:
    def __init__(self, ports: VerticalPipelinePorts, *, project_authorized: Callable[[str, str], bool]):
        if not isinstance(ports, VerticalPipelinePorts):
            raise TypeError("pipeline ports required")
        if not callable(project_authorized):
            raise TypeError("project authorization required")
        for name in ("import_project", "analyze_project", "review_findings", "build_report"):
            if not callable(getattr(ports, name)):
                raise TypeError(f"{name} port required")
        self._ports = ports
        self._project_authorized = project_authorized

    def run(self, project: VerticalProject) -> VerticalPipelineResult:
        if not isinstance(project, VerticalProject):
            raise TypeError("VerticalProject required")
        if self._project_authorized(project.customer_id, project.project_id) is not True:
            raise PermissionError("project not authorized")
        if not project.source_directory.is_dir():
            raise ValueError("project source directory missing")
        imported = self._ports.import_project(project.source_directory)
        if imported is None:
            raise ValueError("import returned no result")
        analysis = self._ports.analyze_project(imported)
        if analysis is None:
            raise ValueError("analysis returned no result")
        review = self._ports.review_findings(analysis)
        if not isinstance(review, ReviewedDecision) or review.approved is not True:
            raise ReviewRequiredError("human review approval required")
        report = self._ports.build_report(analysis, review)
        if report is None:
            raise ValueError("report returned no result")
        return VerticalPipelineResult(project, imported, analysis, review, report)
