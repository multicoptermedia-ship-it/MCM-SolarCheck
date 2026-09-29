from __future__ import annotations

from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_payment_operation import SQLitePaymentOperationIntentStore
from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_capture import PaymentCaptureService
from mcm_solarcheck.services.payment_gateway import PaymentAuthorizationResult


class BillingStore:
    def get(self, job_id: str) -> ComputeJobBilling:
        return ComputeJobBilling(
            ComputeJobDelivery(
                job_id,
                "user-a",
                "project-a",
                export_completed=True,
                report_retrieved=True,
            ),
            billing_released=True,
        )


class RecordingGateway:
    def __init__(self) -> None:
        self.captures: list[tuple[str, str]] = []

    def authorize(
        self, payment: OnlinePayment, *, idempotency_key: str
    ) -> PaymentAuthorizationResult:
        raise AssertionError("authorize not expected")

    def capture(
        self, provider_reference: str, *, idempotency_key: str
    ) -> None:
        self.captures.append((provider_reference, idempotency_key))

    def void(self, provider_reference: str, *, idempotency_key: str) -> None:
        raise AssertionError("void not expected")


def test_delivered_payment_uses_stable_provider_capture_key(tmp_path) -> None:
    payments = SQLiteOnlinePaymentStore(tmp_path / "payment.sqlite")
    payments.create(
        OnlinePayment(
            "payment-a",
            "user-a",
            "project-a",
            "job-a",
            PaymentAmount(45000, "EUR"),
        )
    )
    payments.authorize(
        "payment-a", "user-a", "project-a", "provider-auth-a"
    )
    gateway = RecordingGateway()
    service = PaymentCaptureService(
        payments,
        BillingStore(),
        gateway,
        SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite"),
    )

    captured = service.capture(
        "payment-a", user_id="user-a", project_id="project-a"
    )

    assert captured.status is PaymentStatus.CAPTURED
    assert gateway.captures == [
        ("provider-auth-a", "payment:payment-a:capture")
    ]
