"""Project-scoped, human-reviewed RGB orthophoto report output."""
from pathlib import Path

from mcm_solarcheck.services.orthophoto_report_export import (
    export_pilot_pdf_with_rgb_orthophoto,
)
from mcm_solarcheck.services.pv_report_pilot_contract import PilotReport


def export_reviewed_project_orthophoto_pdf(
    service, project_id: str, report: PilotReport,
    rgb_geotiff: str | Path, destination: str | Path, *, evidence=(),
):
    """Require a persisted project and an explicitly reviewed pilot report.

    Does not infer findings, temperatures or review decisions from imagery.
    """
    if not any(item.project_id == project_id for item in service.projects()):
        raise KeyError(f"Unknown project: {project_id}")
    if not isinstance(report, PilotReport):
        raise TypeError("reviewed PilotReport required")
    return export_pilot_pdf_with_rgb_orthophoto(
        report, rgb_geotiff, destination, evidence=evidence,
    )
