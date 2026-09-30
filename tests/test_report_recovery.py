from __future__ import annotations

import sqlite3

import pytest

from mcm_solarcheck.infrastructure.sqlite_report_recovery import SQLiteReportRecoveryStore
from mcm_solarcheck.services.email import EmailMessage, ReportRecoveryEmailConfig
from mcm_solarcheck.services.report_recovery import ReportRecoveryService
from mcm_solarcheck.services.report_recovery_notification import (
    ReportRecoveryNotificationService,
)


class RecordingEmailSender:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []
        self.fail = False

    def send(self, message: EmailMessage) -> None:
        if self.fail:
            raise RuntimeError("SMTP unavailable")
        self.messages.append(message)


def recovery_service(tmp_path) -> tuple[RecordingEmailSender, ReportRecoveryService]:
    sender = RecordingEmailSender()
    notifications = ReportRecoveryNotificationService(
        sender,
        ReportRecoveryEmailConfig(
            sender="solarcheck@mcm-dronetech.com",
            notify_to="solarcheck@mcm-dronetech.com",
        ),
    )
    claims = SQLiteReportRecoveryStore(tmp_path / "recovery.sqlite")
    return sender, ReportRecoveryService(notifications, claims)


@pytest.mark.parametrize("phase", ["export", "delivery"])
def test_transient_report_failure_does_not_alert_admin(phase, tmp_path) -> None:
    sender, service = recovery_service(tmp_path)

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
def test_terminal_report_failure_alerts_admin_only_once(phase, tmp_path) -> None:
    sender, service = recovery_service(tmp_path)
    report_path = tmp_path / "private" / "reports" / "job-a.pdf"

    first = service.record_failure(
        job_id="job-a",
        project_id="project-a",
        phase=phase,
        report_path=report_path,
        terminal=True,
    )
    second = service.record_failure(
        job_id="job-a",
        project_id="project-a",
        phase=phase,
        report_path=report_path,
        terminal=True,
    )

    assert first is True
    assert second is False
    assert len(sender.messages) == 1
    assert sender.messages[0].recipient == "solarcheck@mcm-dronetech.com"
    assert phase in sender.messages[0].text
    assert "job-a.pdf" in sender.messages[0].text
    assert report_path.exists() is False


def test_failed_admin_email_releases_claim_for_retry(tmp_path) -> None:
    sender, service = recovery_service(tmp_path)
    sender.fail = True

    with pytest.raises(RuntimeError, match="SMTP unavailable"):
        service.record_failure(
            job_id="job-a",
            project_id="project-a",
            phase="delivery",
            report_path=tmp_path / "job-a.pdf",
            terminal=True,
        )

    sender.fail = False
    assert service.record_failure(
        job_id="job-a",
        project_id="project-a",
        phase="delivery",
        report_path=tmp_path / "job-a.pdf",
        terminal=True,
    ) is True
    assert len(sender.messages) == 1


def test_recovery_claim_survives_service_restart(tmp_path) -> None:
    sender, service = recovery_service(tmp_path)
    path = tmp_path / "job-a.pdf"
    assert service.record_failure(
        job_id="job-a", project_id="project-a", phase="export",
        report_path=path, terminal=True,
    ) is True

    notifications = ReportRecoveryNotificationService(
        sender,
        ReportRecoveryEmailConfig(
            sender="solarcheck@mcm-dronetech.com",
            notify_to="solarcheck@mcm-dronetech.com",
        ),
    )
    restarted = ReportRecoveryService(
        notifications,
        SQLiteReportRecoveryStore(tmp_path / "recovery.sqlite"),
    )
    assert restarted.record_failure(
        job_id="job-a", project_id="project-a", phase="export",
        report_path=path, terminal=True,
    ) is False
    assert len(sender.messages) == 1


def test_recovery_rejects_unknown_phase_before_sending(tmp_path) -> None:
    sender, service = recovery_service(tmp_path)

    with pytest.raises(ValueError, match="phase"):
        service.record_failure(
            job_id="job-a",
            project_id="project-a",
            phase="payment",
            report_path=tmp_path / "job-a.pdf",
            terminal=True,
        )

    assert sender.messages == []


def test_expired_pending_recovery_claim_is_retried_after_restart(tmp_path) -> None:
    database = tmp_path / "recovery.sqlite"
    claims = SQLiteReportRecoveryStore(database)
    assert claims.claim("job-a", "delivery") is True

    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            UPDATE report_recovery_notification
            SET lease_until = 0
            WHERE job_id = ? AND phase = ?
            """,
            ("job-a", "delivery"),
        )

    sender = RecordingEmailSender()
    notifications = ReportRecoveryNotificationService(
        sender,
        ReportRecoveryEmailConfig(
            sender="solarcheck@mcm-dronetech.com",
            notify_to="solarcheck@mcm-dronetech.com",
        ),
    )
    restarted = ReportRecoveryService(
        notifications,
        SQLiteReportRecoveryStore(database),
    )

    assert restarted.record_failure(
        job_id="job-a",
        project_id="project-a",
        phase="delivery",
        report_path=tmp_path / "job-a.pdf",
        terminal=True,
    ) is True
    assert len(sender.messages) == 1

    assert restarted.record_failure(
        job_id="job-a",
        project_id="project-a",
        phase="delivery",
        report_path=tmp_path / "job-a.pdf",
        terminal=True,
    ) is False
    assert len(sender.messages) == 1


def test_active_pending_recovery_claim_prevents_parallel_send(tmp_path) -> None:
    database = tmp_path / "recovery.sqlite"
    first = SQLiteReportRecoveryStore(database)
    second = SQLiteReportRecoveryStore(database)

    assert first.claim("job-a", "export") is True
    assert second.claim("job-a", "export") is False
