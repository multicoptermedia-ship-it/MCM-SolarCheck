"""Terminal report failure handling for manual SFTP recovery."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from mcm_solarcheck.services.report_recovery_notification import (
    ReportRecoveryNotificationService,
)


class ReportRecoveryClaimStore(Protocol):
    def claim(self, job_id: str, phase: str) -> bool:
        ...

    def mark_sent(self, job_id: str, phase: str) -> None:
        ...

    def release(self, job_id: str, phase: str) -> None:
        ...


class ReportRecoveryService:
    """Notify operations once after the caller declares a report failure terminal."""

    def __init__(
        self,
        notifications: ReportRecoveryNotificationService,
        claims: ReportRecoveryClaimStore,
    ) -> None:
        self._notifications = notifications
        self._claims = claims

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
        if not self._claims.claim(job_id, phase):
            return False

        try:
            self._notifications.notify(
                job_id=job_id,
                project_id=project_id,
                phase=phase,
                report_path=report_path,
            )
        except Exception:
            self._claims.release(job_id, phase)
            raise
        self._claims.mark_sent(job_id, phase)
        return True
