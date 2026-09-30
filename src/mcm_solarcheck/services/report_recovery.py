"""Terminal report failure handling for manual SFTP recovery."""

from __future__ import annotations

from pathlib import Path

from mcm_solarcheck.services.report_recovery_notification import (
    ReportRecoveryNotificationService,
)


class ReportRecoveryService:
    """Notify operations only after the caller declares a report failure terminal."""

    def __init__(self, notifications: ReportRecoveryNotificationService) -> None:
        self._notifications = notifications

    def record_failure(
        self,
        *,
        job_id: str,
        project_id: str,
        phase: str,
        report_path: str | Path,
        terminal: bool,
    ) -> bool:
        if phase not in {"export", "delivery"}:
            raise ValueError("recovery phase must be export or delivery")
        if not isinstance(terminal, bool):
            raise ValueError("terminal must be a boolean")
        if not terminal:
            return False

        self._notifications.notify(
            job_id=job_id,
            project_id=project_id,
            phase=phase,
            report_path=report_path,
        )
        return True
