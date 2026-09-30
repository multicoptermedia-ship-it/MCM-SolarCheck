from __future__ import annotations

from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_payment_operation import SQLitePaymentOperationIntentStore
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_capture import PaymentCaptureService
from mcm_solarcheck.services.payment_delivery import PaymentDeliveryService
from mcm_solarcheck.services.payment_gateway import PaymentAuthorizationResult


class RecordingGateway:
    def __init__(self) -> None:
        self.captures = []

    def authorize(self, payment, *, idempotency_key):
        return PaymentAuthorizationResult("provider-auth-a")

    def capture(self, provider_reference, *, idempotency_key):
        self.captures.append((provider_reference, idempotency_key))

    def void(self, provider_reference, *, idempotency_key):
        raise AssertionError("void not expected")


def build_delivery_flow(tmp_path):
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    payments.create(
        OnlinePayment(
            "payment-a",
            "user-a",
            "project-a",
            "job-a",
            PaymentAmount(14500, "EUR"),
            tariff_version=1,
            plant_kwp=750,
        )
    )
    payments.authorize(
        "payment-a",
        "user-a",
        "project-a",
        "provider-auth-a",
    )

    billing_store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(billing_store)
    billing.create("job-a", user_id="user-a", project_id="project-a")

    gateway = RecordingGateway()
    capture = PaymentCaptureService(
        payments,
        billing_store,
        gateway,
        SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite"),
    )
    return (
        PaymentDeliveryService(billing, capture),
        payments,
        billing_store,
        gateway,
    )


def test_export_alone_never_captures_payment(tmp_path) -> None:
    service, payments, billing, gateway = build_delivery_flow(tmp_path)

    result = service.mark_export_completed(
        "payment-a",
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert result.payment is None
    assert result.billing.delivery.export_completed
    assert not result.billing.delivery.report_retrieved
    assert not result.billing.billing_released
    assert payments.get("payment-a").status is PaymentStatus.AUTHORIZED
    assert gateway.captures == []


def test_report_retrieval_alone_never_captures_payment(tmp_path) -> None:
    service, payments, billing, gateway = build_delivery_flow(tmp_path)

    result = service.mark_report_retrieved(
        "payment-a",
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert result.payment is None
    assert not result.billing.delivery.export_completed
    assert result.billing.delivery.report_retrieved
    assert not result.billing.billing_released
    assert payments.get("payment-a").status is PaymentStatus.AUTHORIZED
    assert gateway.captures == []


def test_second_delivery_condition_releases_and_captures_once(tmp_path) -> None:
    service, payments, billing, gateway = build_delivery_flow(tmp_path)

    service.mark_export_completed(
        "payment-a",
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )
    result = service.mark_report_retrieved(
        "payment-a",
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert result.billing.delivery.billable
    assert result.billing.billing_released
    assert result.payment is not None
    assert result.payment.status is PaymentStatus.CAPTURED
    assert result.payment.tariff_version == 1
    assert result.payment.plant_kwp == 750
    assert payments.get("payment-a").status is PaymentStatus.CAPTURED
    assert gateway.captures == [
        ("provider-auth-a", "payment:payment-a:capture")
    ]


def test_delivery_order_does_not_change_capture_gate(tmp_path) -> None:
    service, payments, billing, gateway = build_delivery_flow(tmp_path)

    service.mark_report_retrieved(
        "payment-a",
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )
    result = service.mark_export_completed(
        "payment-a",
        "job-a",
        user_id="user-a",
        project_id="project-a",
    )

    assert result.payment is not None
    assert result.payment.status is PaymentStatus.CAPTURED
    assert len(gateway.captures) == 1
