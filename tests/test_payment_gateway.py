from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.services.payment import (
    OnlinePayment,
    PaymentAmount,
    PaymentStatus,
)
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.payment_provider import (
    PaymentProviderCapabilities,
    PaymentProviderRegistry,
)
from mcm_solarcheck.services.payment_routing import PaymentProviderRoutingService
from mcm_solarcheck.services.payment_gateway import (
    PaymentAuthorizationResult,
    PaymentAuthorizationService,
)


class RecordingGateway:
    def __init__(self) -> None:
        self.authorized: list[tuple[OnlinePayment, str]] = []

    def authorize(
        self, payment: OnlinePayment, *, idempotency_key: str
    ) -> PaymentAuthorizationResult:
        self.authorized.append((payment, idempotency_key))
        return PaymentAuthorizationResult("provider-auth-a")

    def capture(self, provider_reference: str, *, idempotency_key: str) -> None:
        raise AssertionError("capture not expected")

    def void(self, provider_reference: str, *, idempotency_key: str) -> None:
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

    assert gateway.authorized[0][0].amount == PaymentAmount(45000, "EUR")
    assert gateway.authorized[0][1] == "payment:payment-a:authorize"
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


def test_authorization_rejects_provider_that_does_not_support_method(tmp_path) -> None:
    store = SQLiteOnlinePaymentStore(tmp_path / "payment-routing.sqlite")
    store.create(
        OnlinePayment(
            "payment-routed",
            "user-a",
            "project-a",
            "job-a",
            PaymentAmount(45000, "EUR"),
            method=PaymentMethod.PAYPAL,
        )
    )
    gateway = RecordingGateway()
    routing = PaymentProviderRoutingService(
        PaymentProviderRegistry(
            (
                PaymentProviderCapabilities(
                    "card-only",
                    frozenset({PaymentMethod.CARD}),
                ),
                PaymentProviderCapabilities(
                    "paypal",
                    frozenset({PaymentMethod.PAYPAL}),
                ),
            )
        )
    )

    wrong = PaymentAuthorizationService(
        store, gateway, routing, "card-only"
    )
    with pytest.raises(ValueError, match="does not support"):
        wrong.authorize(
            "payment-routed", user_id="user-a", project_id="project-a"
        )
    assert gateway.authorized == []

    correct = PaymentAuthorizationService(
        store, gateway, routing, "paypal"
    )
    authorized = correct.authorize(
        "payment-routed", user_id="user-a", project_id="project-a"
    )

    assert authorized.status is PaymentStatus.AUTHORIZED
    assert len(gateway.authorized) == 1


def test_authorization_cannot_switch_bound_payment_provider(tmp_path) -> None:
    store = SQLiteOnlinePaymentStore(tmp_path / "payment-bound-provider.sqlite")
    store.create(
        OnlinePayment(
            "payment-bound",
            "user-a",
            "project-a",
            "job-bound",
            PaymentAmount(45000, "EUR"),
            method=PaymentMethod.PAYPAL,
            provider_id="paypal-a",
        )
    )
    gateway = RecordingGateway()
    routing = PaymentProviderRoutingService(
        PaymentProviderRegistry(
            (
                PaymentProviderCapabilities(
                    "paypal-a",
                    frozenset({PaymentMethod.PAYPAL}),
                ),
                PaymentProviderCapabilities(
                    "paypal-b",
                    frozenset({PaymentMethod.PAYPAL}),
                ),
            )
        )
    )
    service = PaymentAuthorizationService(
        store, gateway, routing, "paypal-b"
    )

    with pytest.raises(ValueError, match="provider snapshot mismatch"):
        service.authorize(
            "payment-bound", user_id="user-a", project_id="project-a"
        )

    assert gateway.authorized == []
    assert store.get("payment-bound").status is PaymentStatus.CREATED
