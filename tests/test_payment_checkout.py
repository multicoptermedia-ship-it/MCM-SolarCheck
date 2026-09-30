from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_merchant_account import SQLiteMerchantAccountStore
from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_voucher import SQLiteFlightPlanVoucherStore
from mcm_solarcheck.services.merchant_account import MerchantAccount, MerchantAccountKind
from mcm_solarcheck.services.merchant_binding import MerchantAccountBindingService
from mcm_solarcheck.services.payment import PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_checkout import OnlinePaymentCheckoutService
from mcm_solarcheck.services.payment_gateway import (
    PaymentAuthorizationResult,
    PaymentAuthorizationService,
)
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.payment_pricing import PaymentPricingService
from mcm_solarcheck.services.payment_provider import (
    PaymentProviderCapabilities,
    PaymentProviderRegistry,
)
from mcm_solarcheck.services.payment_routing import PaymentProviderRoutingService
from mcm_solarcheck.services.voucher_admin import FlightPlanVoucherPolicy


class RecordingGateway:
    def __init__(self) -> None:
        self.authorizations = []

    def authorize(self, payment, *, idempotency_key):
        self.authorizations.append((payment, idempotency_key))
        return PaymentAuthorizationResult("provider-payment-a")

    def capture(self, provider_reference, *, idempotency_key):
        raise AssertionError("checkout must not capture")

    def void(self, provider_reference, *, idempotency_key):
        raise AssertionError("checkout must not void")


def build_checkout(tmp_path, method, kind):
    payments = SQLiteOnlinePaymentStore(tmp_path / "payments.sqlite")
    vouchers = SQLiteFlightPlanVoucherStore(tmp_path / "vouchers.sqlite")
    accounts = SQLiteMerchantAccountStore(tmp_path / "merchants.sqlite")
    accounts.save(
        MerchantAccount(
            "merchant-a",
            "provider-a",
            kind,
            "merchant display",
        )
    )
    providers = PaymentProviderRegistry(
        (PaymentProviderCapabilities("provider-a", frozenset({method})),)
    )
    gateway = RecordingGateway()
    checkout = OnlinePaymentCheckoutService(
        PaymentPricingService(payments, vouchers, FlightPlanVoucherPolicy()),
        MerchantAccountBindingService(accounts),
        providers,
        PaymentAuthorizationService(
            payments,
            gateway,
            PaymentProviderRoutingService(providers),
            "provider-a",
        ),
        payments,
    )
    return checkout, payments, gateway


def test_checkout_persists_card_routing_snapshot_before_authorization(tmp_path) -> None:
    checkout, payments, gateway = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
    )

    result = checkout.checkout(
        "payment-a",
        user_id="user-a",
        project_id="project-a",
        job_id="job-a",
        base_amount=PaymentAmount(50000, "EUR"),
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-a",
        now=datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc),
    )

    assert result.status is PaymentStatus.AUTHORIZED
    assert result.method is PaymentMethod.CARD
    assert result.merchant_account_id == "merchant-a"
    assert result.merchant_account_version == 1
    assert result.provider_id == "provider-a"
    assert payments.get("payment-a") == result
    assert len(gateway.authorizations) == 1
    provider_payment, key = gateway.authorizations[0]
    assert provider_payment.method is PaymentMethod.CARD
    assert provider_payment.merchant_account_id == "merchant-a"
    assert provider_payment.provider_id == "provider-a"
    assert key == "payment:payment-a:authorize"


def test_checkout_does_not_send_sepa_through_authorization_gateway(tmp_path) -> None:
    checkout, payments, gateway = build_checkout(
        tmp_path,
        PaymentMethod.SEPA_DIRECT_DEBIT,
        MerchantAccountKind.BANK,
    )

    with pytest.raises(ValueError, match="dedicated processing flow"):
        checkout.checkout(
            "payment-sepa",
            user_id="user-a",
            project_id="project-a",
            job_id="job-sepa",
            base_amount=PaymentAmount(50000, "EUR"),
            method=PaymentMethod.SEPA_DIRECT_DEBIT,
            provider_id="provider-a",
            merchant_account_id="merchant-a",
            now=datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc),
        )

    assert gateway.authorizations == []
    persisted = payments.get("payment-sepa")
    assert persisted.status is PaymentStatus.CREATED
    assert persisted.method is None
    assert persisted.provider_id is None
