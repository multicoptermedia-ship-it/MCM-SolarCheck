"""Offline-first composition boundary for the shared vertical inspection core.

Deployment must explicitly provide real analysis, human review and report
implementations. No placeholder or fabricated findings are permitted.
"""
from __future__ import annotations

from typing import Callable

from mcm_solarcheck.importers.project import import_m3t_project
from mcm_solarcheck.services.vertical_inspection_pipeline import VerticalInspectionPipeline
from mcm_solarcheck.services.vertical_pipeline_contracts import VerticalPipelinePorts


def build_m3t_vertical_pipeline(
    *,
    project_authorized: Callable[[str, str], bool],
    analyze_project: Callable[[object], object],
    review_findings: Callable[[object], object],
    build_report: Callable[[object, object], object],
    import_project=import_m3t_project,
) -> VerticalInspectionPipeline:
    """Wire the existing DJI M3T importer into the shared, opt-in pipeline."""
    return VerticalInspectionPipeline(
        VerticalPipelinePorts(
            import_project=import_project,
            analyze_project=analyze_project,
            review_findings=review_findings,
            build_report=build_report,
        ),
        project_authorized=project_authorized,
    )
