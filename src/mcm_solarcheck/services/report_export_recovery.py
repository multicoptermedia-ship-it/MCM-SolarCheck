"""Private report export orchestration with terminal recovery alerts."""

from __future__ import annotations

from pathlib import Path

from mcm_solarcheck.reporting.report_model import InspectionReport
from mcm_solarcheck.services.billing import ComputeJobBilling
from mcm_solarcheck.services.private_report_export import PrivateReportExportService
from mcm_solarcheck.services.report_recovery import ReportRecoveryService


class ReportExportRecoveryService:
    def __init__(
        self,
        export: PrivateReportExportService,
        recovery: ReportRecoveryService,
    ) -> None:
        self._export = export
        self._recovery = recovery

    def export(
        self,
        report: InspectionReport,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
        report_path: str | Path,
        terminal_on_failure: bool,
        banner_path: str | Path | None = None,
    ) -> ComputeJobBilling:
        try:
            return self._export.export(
                report,
                job_id,
                user_id=user_id,
                project_id=project_id,
                banner_path=banner_path,
            )
        except Exception as export_error:
            try:
                self._recovery.record_failure(
                    job_id=job_id,
                    project_id=project_id,
                    phase="export",
                    report_path=report_path,
                    terminal=terminal_on_failure,
                )
            except Exception as recovery_error:
                raise export_error from recovery_error
            raise
