from __future__ import annotations

import pytest

from mcm_solarcheck.services.email import EmailMessage, ReportRecoveryEmailConfig
from mcm_solarcheck.services.report_recovery import ReportRecoveryService
from mcm_solarcheck.services.report_recovery_notification import (
    ReportRecoveryNotificationService,
)


class RecordingEmailSender:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


def recovery_service() -> tuple[RecordingEmailSender, ReportRecoveryService]:
    sender = RecordingEmailSender()
    notifications = ReportRecoveryNotificationService(
        sender,
        ReportRecoveryEmailConfig(
            sender="solarcheck@mcm-dronetech.com",
            notify_to="solarcheck@mcm-dronetech.com",
        ),
    )
    return sender, ReportRecoveryService(notifications)


@pytest.mark.parametrize("phase", ["export", "delivery"])
def test_transient_report_failure_does_not_alert_admin(phase, tmp_path) -> None:
    sender, service = recovery_service()

    notified = service.record_failure(
        job_id="job-a",
        project_id="project-a",
        phase=phase,
        report_path=tmp_path / "private" / "reports" / "job-a.pdf",
        terminal=False,
    )

    assert notified is False
    assert sender.messages == []


@pytest.mark.parametrize("phase", ["export", "delivery"])
def test_terminal_report_failure_alerts_admin_once_per_call(phase, tmp_path) -> None:
    sender, service = recovery_service()
    report_path = tmp_path / "private" / "reports" / "job-a.pdf"

    notified = service.record_failure(
        job_id="job-a",
        project_id="project-a",
        phase=phase,
        report_path=report_path,
        terminal=True,
    )

    assert notified is True
    assert len(sender.messages) == 1
    assert sender.messages[0].recipient == "solarcheck@mcm-dronetech.com"
    assert phase in sender.messages[0].text
    assert "job-a.pdf" in sender.messages[0].text
    assert report_path.exists() is False


def test_recovery_rejects_unknown_phase_before_sending(tmp_path) -> None:
    sender, service = recovery_service()

    with pytest.raises(ValueError, match="phase"):
        service.record_failure(
            job_id="job-a",
            project_id="project-a",
            phase="payment",
            report_path=tmp_path / "job-a.pdf",
            terminal=True,
        )

    assert sender.messages == []
