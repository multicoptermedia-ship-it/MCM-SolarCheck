"""Report delivery orchestration with terminal manual-recovery alerts."""

from __future__ import annotations

from pathlib import Path

from mcm_solarcheck.services.billing import ComputeJobBilling
from mcm_solarcheck.services.report_delivery import ReportDeliveryService, ReportSender
from mcm_solarcheck.services.report_recovery import ReportRecoveryService


class ReportDeliveryRecoveryService:
    """Preserve delivery failures while optionally recording terminal recovery."""

    def __init__(
        self,
        delivery: ReportDeliveryService,
        recovery: ReportRecoveryService,
    ) -> None:
        self._delivery = delivery
        self._recovery = recovery

    def deliver(
        self,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
        report_path: str | Path,
        send: ReportSender,
        terminal_on_failure: bool,
    ) -> ComputeJobBilling:
        try:
            return self._delivery.deliver(
                job_id,
                user_id=user_id,
                project_id=project_id,
                send=send,
            )
        except Exception as delivery_error:
            try:
                self._recovery.record_failure(
                    job_id=job_id,
                    project_id=project_id,
                    phase="delivery",
                    report_path=report_path,
                    terminal=terminal_on_failure,
                )
            except Exception as recovery_error:
                raise delivery_error from recovery_error
            raise
