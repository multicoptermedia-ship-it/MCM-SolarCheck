from __future__ import annotations

from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_payment_operation import SQLitePaymentOperationIntentStore
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_gateway import PaymentAuthorizationResult
from mcm_solarcheck.services.payment_void import PaymentVoidService


class RecordingGateway:
    def __init__(self) -> None:
        self.voids: list[tuple[str, str]] = []

    def authorize(
        self, payment: OnlinePayment, *, idempotency_key: str
    ) -> PaymentAuthorizationResult:
        raise AssertionError("authorize not expected")

    def capture(self, provider_reference: str, *, idempotency_key: str) -> None:
        raise AssertionError("capture not expected")

    def void(self, provider_reference: str, *, idempotency_key: str) -> None:
        self.voids.append((provider_reference, idempotency_key))


def test_authorized_payment_uses_stable_provider_void_key(tmp_path) -> None:
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

    voided = PaymentVoidService(
        payments,
        gateway,
        SQLitePaymentOperationIntentStore(tmp_path / "operations.sqlite"),
    ).void(
        "payment-a", user_id="user-a", project_id="project-a"
    )

    assert voided.status is PaymentStatus.VOIDED
    assert gateway.voids == [
        ("provider-auth-a", "payment:payment-a:void")
    ]
