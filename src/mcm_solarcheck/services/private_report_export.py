"""Export reports into private filesystem storage and persist completion evidence."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from mcm_solarcheck.infrastructure.filesystem_report import FileSystemReportArtifactStore
from mcm_solarcheck.reporting.export import export_report
from mcm_solarcheck.reporting.report_model import InspectionReport
from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobBillingStore


class PrivateReportExportService:
    """Create a report artifact before making export completion authoritative."""

    def __init__(
        self,
        billing: ComputeJobBillingStore,
        reports: FileSystemReportArtifactStore,
    ) -> None:
        self._billing = billing
        self._reports = reports

    def export(
        self,
        report: InspectionReport,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
        banner_path: str | Path | None = None,
    ) -> ComputeJobBilling:
        current = self._billing.get(job_id)
        if (
            current.delivery.user_id != user_id
            or current.delivery.project_id != project_id
        ):
            raise PermissionError("report export ownership mismatch")
        if report.project_id != project_id:
            raise ValueError("report project does not match compute job")

        destination = self._reports.path_for(job_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.stem}-",
            suffix=f"{self._reports.suffix}.tmp",
            dir=destination.parent,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            export_report(
                report,
                temporary,
                format=self._reports.suffix.lstrip("."),
                banner_path=banner_path,
            )
            if not temporary.is_file() or temporary.stat().st_size == 0:
                raise RuntimeError("report export did not create artifact")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)

        return self._billing.mark_export_completed(job_id, user_id, project_id)
