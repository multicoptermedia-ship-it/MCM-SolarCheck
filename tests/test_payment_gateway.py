from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.services.payment import (
    OnlinePayment,
    PaymentAmount,
    PaymentStatus,
)
from mcm_solarcheck.services.payment_gateway import (
    PaymentAuthorizationResult,
    PaymentAuthorizationService,
)


class RecordingGateway:
    def __init__(self) -> None:
        self.authorized: list[OnlinePayment] = []

    def authorize(self, payment: OnlinePayment) -> PaymentAuthorizationResult:
        self.authorized.append(payment)
        return PaymentAuthorizationResult("provider-auth-a")

    def capture(self, provider_reference: str) -> None:
        raise AssertionError("capture not expected")

    def void(self, provider_reference: str) -> None:
        raise AssertionError("void not expected")


def test_gateway_receives_fixed_payable_amount(tmp_path) -> None:
    store = SQLiteOnlinePaymentStore(tmp_path / "payment.sqlite")
    store.create(
        OnlinePayment(
            "payment-a",
            "user-a",
            "project-a",
            "job-a",
            PaymentAmount(45000, "EUR"),
        )
    )
    gateway = RecordingGateway()
    service = PaymentAuthorizationService(store, gateway)

    authorized = service.authorize(
        "payment-a", user_id="user-a", project_id="project-a"
    )

    assert gateway.authorized[0].amount == PaymentAmount(45000, "EUR")
    assert authorized.status is PaymentStatus.AUTHORIZED
    assert authorized.provider_reference == "provider-auth-a"


def test_settled_zero_amount_payment_never_reaches_gateway(tmp_path) -> None:
    store = SQLiteOnlinePaymentStore(tmp_path / "payment.sqlite")
    store.create(
        OnlinePayment(
            "payment-free",
            "user-a",
            "project-a",
            "job-a",
            None,
            PaymentStatus.SETTLED,
        )
    )
    gateway = RecordingGateway()
    service = PaymentAuthorizationService(store, gateway)

    with pytest.raises(ValueError, match="no provider authorization"):
        service.authorize(
            "payment-free", user_id="user-a", project_id="project-a"
        )

    assert gateway.authorized == []
