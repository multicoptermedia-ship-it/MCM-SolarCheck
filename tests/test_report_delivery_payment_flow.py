from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_payment_operation import (
    SQLitePaymentOperationIntentStore,
)
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_capture import PaymentCaptureService
from mcm_solarcheck.services.report_delivery import ReportArtifact, ReportDeliveryService


class ReportStore:
    def get(self, job_id: str) -> ReportArtifact:
        return ReportArtifact(
            job_id,
            b"confidential SolarCheck report",
            "application/pdf",
            "solarcheck.pdf",
        )


class RecordingGateway:
    def __init__(self) -> None:
        self.captures: list[tuple[str, str]] = []

    def capture(self, provider_reference: str, *, idempotency_key: str) -> None:
        self.captures.append((provider_reference, idempotency_key))


def setup_flow(tmp_path):
    billing_store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(billing_store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    billing.mark_export_completed(
        "job-a", user_id="user-a", project_id="project-a"
    )

    payments = SQLiteOnlinePaymentStore(tmp_path / "payment.sqlite")
    payments.create(
        OnlinePayment(
            "payment-a",
            "user-a",
            "project-a",
            "job-a",
            PaymentAmount(12900, "EUR"),
        )
    )
    payments.authorize(
        "payment-a",
        "user-a",
        "project-a",
        "provider-auth-a",
    )

    gateway = RecordingGateway()
    capture = PaymentCaptureService(
        payments,
        billing_store,
        gateway,
        SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite"),
    )
    delivery = ReportDeliveryService(billing_store, ReportStore())
    return billing_store, payments, gateway, capture, delivery


def test_failed_report_delivery_keeps_payment_authorized(tmp_path) -> None:
    billing, payments, gateway, capture, delivery = setup_flow(tmp_path)

    def disconnect(_report: ReportArtifact) -> None:
        raise OSError("client disconnected")

    with pytest.raises(OSError, match="client disconnected"):
        delivery.deliver(
            "job-a",
            user_id="user-a",
            project_id="project-a",
            send=disconnect,
        )

    with pytest.raises(ValueError, match="export and report retrieval"):
        capture.capture(
            "payment-a",
            user_id="user-a",
            project_id="project-a",
        )

    assert billing.get("job-a").delivery.report_retrieved is False
    assert billing.get("job-a").billing_released is False
    assert payments.get("payment-a").status is PaymentStatus.AUTHORIZED
    assert gateway.captures == []


def test_successful_delivery_allows_exactly_one_provider_capture(tmp_path) -> None:
    billing, payments, gateway, capture, delivery = setup_flow(tmp_path)
    sent: list[ReportArtifact] = []

    released = delivery.deliver(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        send=sent.append,
    )
    first = capture.capture(
        "payment-a",
        user_id="user-a",
        project_id="project-a",
    )
    second = capture.capture(
        "payment-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert len(sent) == 1
    assert released.delivery.report_retrieved is True
    assert released.billing_released is True
    assert first.status is PaymentStatus.CAPTURED
    assert second == first
    assert payments.get("payment-a") == first
    assert gateway.captures == [
        ("provider-auth-a", "payment:payment-a:capture")
    ]
