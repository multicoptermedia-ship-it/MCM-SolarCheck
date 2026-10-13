"""Guarded export through the existing DOCX, ODT and PDF report renderers."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from mcm_solarcheck.reporting.export import export_report
from mcm_solarcheck.reporting.report_model import InspectionReport
from mcm_solarcheck.services.vertical_pipeline_contracts import ReviewRequiredError


def export_reviewed_inspection(
    report: InspectionReport,
    destination: str | Path,
    *,
    authorize_export: Callable[[str], bool],
    format: str | None = None,
) -> Path:
    """Opt-in local export; online payment/delivery authorization is separate."""
    if not isinstance(report, InspectionReport):
        raise TypeError("InspectionReport required")
    if report.release_status != "reviewed":
        raise ReviewRequiredError("only reviewed inspection reports may be exported")
    if not callable(authorize_export) or authorize_export(report.project_id) is not True:
        raise PermissionError("report export not authorized")
    return export_report(report, destination, format=format)
