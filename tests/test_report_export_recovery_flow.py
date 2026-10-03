from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from mcm_solarcheck.infrastructure.filesystem_report import FileSystemReportArtifactStore
from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.infrastructure.sqlite_report_recovery import SQLiteReportRecoveryStore
from mcm_solarcheck.reporting.report_model import InspectionReport
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.email import EmailMessage, ReportRecoveryEmailConfig
from mcm_solarcheck.services.private_report_export import PrivateReportExportService
from mcm_solarcheck.services.report_delivery import ReportDeliveryService
from mcm_solarcheck.services.report_export_recovery import ReportExportRecoveryService
from mcm_solarcheck.services.report_recovery import ReportRecoveryService
from mcm_solarcheck.services.report_recovery_notification import (
    ReportRecoveryNotificationService,
)


class FailingEmailSender:
    def send(self, message: EmailMessage) -> None:
        raise OSError("recovery SMTP unavailable")


def inspection_report() -> InspectionReport:
    return InspectionReport(
        "report-a",
        "project-a",
        "Customer",
        "Site",
        datetime(2026, 9, 30, 12, tzinfo=timezone.utc),
        "Inspector",
        10,
        0,
        0,
    )


def test_export_and_recovery_email_failure_keep_report_inaccessible(tmp_path) -> None:
    billing_store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(billing_store)
    billing.create("job-a", user_id="user-a", project_id="project-a")

    reports = FileSystemReportArtifactStore(tmp_path / "private" / "reports")
    recovery = ReportRecoveryService(
        ReportRecoveryNotificationService(
            FailingEmailSender(),
            ReportRecoveryEmailConfig(
                sender="solarcheck@mcm-dronetech.com",
                notify_to="solarcheck@mcm-dronetech.com",
            ),
        ),
        SQLiteReportRecoveryStore(tmp_path / "recovery.sqlite"),
    )
    service = ReportExportRecoveryService(
        PrivateReportExportService(billing_store, reports),
        recovery,
    )

    def fail_after_partial_write(report, destination, **kwargs) -> None:
        destination.write_bytes(b"partial report")
        raise RuntimeError("renderer failed")

    with patch(
        "mcm_solarcheck.services.private_report_export.export_report",
        side_effect=fail_after_partial_write,
    ):
        with pytest.raises(RuntimeError, match="renderer failed"):
            service.export(
                inspection_report(),
                "job-a",
                user_id="user-a",
                project_id="project-a",
                report_path=reports.path_for("job-a"),
                terminal_on_failure=True,
            )

    state = billing_store.get("job-a")
    assert state.delivery.export_completed is False
    assert state.delivery.report_retrieved is False
    assert state.billing_released is False
    assert reports.path_for("job-a").exists() is False
    assert list(reports.root.glob(".*.tmp")) == []

    delivery = ReportDeliveryService(billing_store, reports)
    with pytest.raises(ValueError, match="unavailable until export"):
        delivery.retrieve("job-a", user_id="user-a", project_id="project-a")


def test_export_project_mismatch_does_not_create_recovery_claim(tmp_path) -> None:
    billing_store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(billing_store)
    billing.create("job-a", user_id="user-a", project_id="other-project")
    reports = FileSystemReportArtifactStore(tmp_path / "private" / "reports")
    claims = SQLiteReportRecoveryStore(tmp_path / "recovery.sqlite")
    recovery = ReportRecoveryService(
        ReportRecoveryNotificationService(
            FailingEmailSender(),
            ReportRecoveryEmailConfig(
                sender="solarcheck@mcm-dronetech.com",
                notify_to="solarcheck@mcm-dronetech.com",
            ),
        ),
        claims,
    )
    service = ReportExportRecoveryService(
        PrivateReportExportService(billing_store, reports),
        recovery,
    )

    with pytest.raises(ValueError, match="project"):
        service.export(
            inspection_report(),
            "job-a",
            user_id="user-a",
            project_id="other-project",
            report_path=reports.path_for("job-a"),
            terminal_on_failure=True,
        )

    assert claims.claim("job-a", "export") is True
