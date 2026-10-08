from __future__ import annotations

from mcm_solarcheck.services.email import (
    EmailMessage,
    ReportRecoveryEmailConfig,
)
from mcm_solarcheck.services.report_recovery_notification import (
    ReportRecoveryNotificationService,
)


class RecordingEmailSender:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


def test_recovery_alert_contains_only_operational_report_reference(tmp_path) -> None:
    sender = RecordingEmailSender()
    service = ReportRecoveryNotificationService(
        sender,
        ReportRecoveryEmailConfig(
            sender="solarcheck@mcm-solarcheck.de",
            notify_to="solarcheck@mcm-dronetech.com",
        ),
    )

    service.notify(
        job_id="job-a",
        project_id="project-a",
        phase="delivery",
        report_path=tmp_path / "private" / "reports" / "job-a.pdf",
    )

    assert len(sender.messages) == 1
    message = sender.messages[0]
    assert message.recipient == "solarcheck@mcm-dronetech.com"
    assert "job-a" in message.text
    assert "project-a" in message.text
    assert "delivery" in message.text
    assert "job-a.pdf" in message.text
    assert str(tmp_path) not in message.text
    assert "SFTP" in message.text
    assert "payment" not in message.text.lower()
    assert "report contents" not in message.text.lower()


def test_recovery_alert_does_not_need_or_read_report_file(tmp_path) -> None:
    sender = RecordingEmailSender()
    service = ReportRecoveryNotificationService(
        sender,
        ReportRecoveryEmailConfig(
            sender="solarcheck@mcm-solarcheck.de",
            notify_to="solarcheck@mcm-dronetech.com",
        ),
    )
    missing = tmp_path / "private" / "reports" / "job-missing.pdf"

    service.notify(
        job_id="job-missing",
        project_id="project-a",
        phase="export",
        report_path=missing,
    )

    assert missing.exists() is False
    assert len(sender.messages) == 1
    assert "job-missing.pdf" in sender.messages[0].text
