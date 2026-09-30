from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_report_recovery import SQLiteReportRecoveryStore
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.email import EmailMessage, ReportRecoveryEmailConfig
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_capture import PaymentCaptureService
from mcm_solarcheck.services.report_delivery import ReportArtifact, ReportDeliveryService
from mcm_solarcheck.services.report_delivery_recovery import ReportDeliveryRecoveryService
from mcm_solarcheck.services.report_recovery import ReportRecoveryService
from mcm_solarcheck.services.report_recovery_notification import (
    ReportRecoveryNotificationService,
)


class ReportStore:
    def get(self, job_id: str) -> ReportArtifact:
        return ReportArtifact(job_id, b"private report", "application/pdf", f"{job_id}.pdf")


class FailingEmailSender:
    def send(self, message: EmailMessage) -> None:
        raise OSError("recovery SMTP unavailable")


def test_delivery_and_recovery_email_failure_never_unlock_billing_or_payment(tmp_path) -> None:
    billing_store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(billing_store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    billing.mark_export_completed("job-a", user_id="user-a", project_id="project-a")

    payments = SQLiteOnlinePaymentStore(tmp_path / "payment.sqlite")
    payments.create(
        OnlinePayment(
            "payment-a", "user-a", "project-a", "job-a",
            PaymentAmount(12900, "EUR"),
        )
    )
    payments.authorize("payment-a", "user-a", "project-a", "provider-auth-a")
    capture = PaymentCaptureService(payments, billing_store)

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
    service = ReportDeliveryRecoveryService(
        ReportDeliveryService(billing_store, ReportStore()),
        recovery,
    )

    def failed_transport(_report: ReportArtifact) -> None:
        raise OSError("customer delivery failed")

    with pytest.raises(OSError, match="customer delivery failed"):
        service.deliver(
            "job-a",
            user_id="user-a",
            project_id="project-a",
            report_path=tmp_path / "private" / "reports" / "job-a.pdf",
            send=failed_transport,
            terminal_on_failure=True,
        )

    state = billing_store.get("job-a")
    assert state.delivery.export_completed is True
    assert state.delivery.report_retrieved is False
    assert state.billing_released is False

    with pytest.raises(ValueError, match="export and report retrieval"):
        capture.capture("payment-a", user_id="user-a", project_id="project-a")

    assert payments.get("payment-a").status is PaymentStatus.AUTHORIZED


def test_transient_delivery_failure_does_not_claim_recovery(tmp_path) -> None:
    billing_store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(billing_store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    billing.mark_export_completed("job-a", user_id="user-a", project_id="project-a")

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
    service = ReportDeliveryRecoveryService(
        ReportDeliveryService(billing_store, ReportStore()),
        recovery,
    )

    with pytest.raises(OSError, match="temporary disconnect"):
        service.deliver(
            "job-a",
            user_id="user-a",
            project_id="project-a",
            report_path=tmp_path / "job-a.pdf",
            send=lambda _report: (_ for _ in ()).throw(OSError("temporary disconnect")),
            terminal_on_failure=False,
        )

    assert claims.claim("job-a", "delivery") is True
