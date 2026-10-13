"""Map existing expert-reviewed inspection reports into the pilot report contract."""
from __future__ import annotations

from mcm_solarcheck.reporting.report_model import InspectionReport
from mcm_solarcheck.services.pv_report_pilot_contract import PilotFinding, PilotReport


def from_reviewed_inspection(report: InspectionReport, *, limitations: str) -> PilotReport:
    if not isinstance(report, InspectionReport):
        raise TypeError("InspectionReport required")
    if report.release_status != "reviewed":
        raise PermissionError("pilot requires expert-reviewed inspection")
    if not limitations.strip():
        raise ValueError("inspection limitations required")
    findings = tuple(
        PilotFinding(
            module=item.module_id,
            observation=item.finding_label or "Unklar; manuelle Prüfung erforderlich",
            reviewed=True,
        )
        for item in report.details
    )
    conditions = None
    if report.irradiance is not None:
        conditions = (
            f"Einstrahlung (Mittel): {report.irradiance.mean_w_m2:g} W/m²; "
            f"Quelle: {report.irradiance.source}"
        )
    return PilotReport(
        project=report.project_id,
        inspection_date=report.inspection_started_at.isoformat(),
        inspector=report.inspector,
        plant=report.site_name,
        conditions=conditions,
        limitations=limitations,
        findings=findings,
    )
