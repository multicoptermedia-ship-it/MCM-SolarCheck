"""Internal alert for manual SFTP report recovery."""

from __future__ import annotations

from pathlib import Path

from mcm_solarcheck.services.email import (
    EmailMessage,
    EmailSender,
    ReportRecoveryEmailConfig,
)


class ReportRecoveryNotificationService:
    """Notify operations without reading reports or changing delivery state."""

    def __init__(
        self,
        sender: EmailSender,
        config: ReportRecoveryEmailConfig,
    ) -> None:
        self._sender = sender
        self._config = config

    def notify(
        self,
        *,
        job_id: str,
        project_id: str,
        phase: str,
        report_path: str | Path,
    ) -> None:
        for name, value in (
            ("job_id", job_id),
            ("project_id", project_id),
            ("phase", phase),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")

        filename = Path(report_path).name
        if not filename:
            raise ValueError("report_path must contain a filename")

        self._sender.send(
            EmailMessage(
                sender=self._config.sender,
                recipient=self._config.notify_to,
                subject="SolarCheck: Report manuell pruefen",
                text=(
                    "Die automatische Report-Verarbeitung benoetigt eine "
                    "manuelle Pruefung.\n\n"
                    f"Job-ID: {job_id.strip()}\n"
                    f"Projekt-ID: {project_id.strip()}\n"
                    f"Fehlerphase: {phase.strip()}\n"
                    f"Report-Datei: {filename}\n\n"
                    "Bitte den privaten Report-Speicher ausschliesslich "
                    "ueber den vorgesehenen SFTP-Zugang pruefen.\n"
                ),
            )
        )
