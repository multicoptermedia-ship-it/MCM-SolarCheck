from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_introductory_offer import SQLiteIntroductoryOfferStore
from mcm_solarcheck.infrastructure.sqlite_merchant_account import SQLiteMerchantAccountStore
from mcm_solarcheck.infrastructure.sqlite_payment import SQLiteOnlinePaymentStore
from mcm_solarcheck.infrastructure.sqlite_solarcheck_tariff import SQLiteSolarCheckTariffStore
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
from mcm_solarcheck.services.solarcheck_tariff import initial_solarcheck_tariff


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


def build_checkout(tmp_path, method, kind, *, introductory_offers=None, registrations=None):
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
    tariffs = SQLiteSolarCheckTariffStore(tmp_path / "tariffs.sqlite")
    tariffs.save(
        initial_solarcheck_tariff(
            datetime(2026, 9, 30, 0, 0, tzinfo=timezone.utc)
        )
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
        tariffs,
        introductory_offers=introductory_offers,
        registrations=registrations,
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
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-a",
        now=datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc),
    )

    assert result.status is PaymentStatus.AUTHORIZED
    assert result.amount == PaymentAmount(14500, "EUR")
    assert result.tariff_version == 1
    assert result.plant_kwp == 750
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
            plant_kwp=750,
            method=PaymentMethod.SEPA_DIRECT_DEBIT,
            provider_id="provider-a",
            merchant_account_id="merchant-a",
            now=datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc),
        )

    assert gateway.authorizations == []
    with pytest.raises(KeyError):
        payments.get("payment-sepa")


def test_checkout_uses_new_tariff_version_after_effective_time(tmp_path) -> None:
    checkout, payments, gateway = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
    )
    tariffs = SQLiteSolarCheckTariffStore(tmp_path / "tariffs.sqlite")
    original = initial_solarcheck_tariff(
        datetime(2026, 9, 30, 0, 0, tzinfo=timezone.utc)
    )
    from mcm_solarcheck.services.solarcheck_tariff import (
        SolarCheckPriceBand,
        SolarCheckTariff,
    )

    edited = SolarCheckTariff(
        2,
        tuple(
            SolarCheckPriceBand(
                band.min_kwp,
                band.max_kwp,
                PaymentAmount(
                    16900 if band.min_kwp == 500 else band.amount.minor_units,
                    "EUR",
                ),
            )
            for band in original.bands
        ),
        datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc),
    )
    tariffs.save(edited)

    result = checkout.checkout(
        "payment-new-tariff",
        user_id="user-a",
        project_id="project-a",
        job_id="job-new-tariff",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-a",
        now=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
    )

    assert result.amount == PaymentAmount(16900, "EUR")
    assert result.tariff_version == 2
    assert result.plant_kwp == 750
    persisted = payments.get("payment-new-tariff")
    assert persisted.amount == PaymentAmount(16900, "EUR")
    assert persisted.tariff_version == 2
    assert persisted.plant_kwp == 750
    assert len(gateway.authorizations) == 1


def test_checkout_applies_introductory_offer_only_while_reserved(tmp_path) -> None:
    offers = SQLiteIntroductoryOfferStore(tmp_path / "offers.sqlite")
    class VerifiedRegistrations:
        def get(self, user_id):
            from mcm_solarcheck.services.registration import OnlineRegistration
            return OnlineRegistration(
                user_id,
                "Customer",
                "customer@example.com",
            ).verify(datetime(2026, 10, 1, tzinfo=timezone.utc))

    checkout, payments, gateway = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
        introductory_offers=offers,
        registrations=VerifiedRegistrations(),
    )

    result = checkout.checkout(
        "payment-intro",
        user_id="user-intro",
        project_id="project-a",
        job_id="job-intro",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-a",
        now=datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc),
    )

    assert result.amount == PaymentAmount(5900, "EUR")
    assert offers.has_used("user-intro") is False


def test_checkout_uses_regular_tariff_after_offer_deadline(tmp_path) -> None:
    offers = SQLiteIntroductoryOfferStore(tmp_path / "offers.sqlite")
    class Registrations:
        def get(self, user_id):
            raise AssertionError("expired offer must not query registration")

    checkout, payments, gateway = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
        introductory_offers=offers,
        registrations=Registrations(),
    )
    result = checkout.checkout(
        "payment-after-offer",
        user_id="user-a",
        project_id="project-a",
        job_id="job-after-offer",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-a",
        now=datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc),
    )
    assert result.amount == PaymentAmount(14500, "EUR")


def test_unregistered_customer_keeps_regular_card_price(tmp_path) -> None:
    offers = SQLiteIntroductoryOfferStore(tmp_path / "offers.sqlite")
    class MissingRegistrations:
        def get(self, user_id):
            raise KeyError(user_id)

    checkout, payments, gateway = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
        introductory_offers=offers,
        registrations=MissingRegistrations(),
    )
    result = checkout.checkout(
        "payment-unregistered",
        user_id="user-unregistered",
        project_id="project-a",
        job_id="job-unregistered",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-a",
        now=datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc),
    )
    assert result.amount == PaymentAmount(14500, "EUR")
    assert offers.has_used("user-unregistered") is False


def test_failed_authorization_releases_introductory_offer(tmp_path) -> None:
    offers = SQLiteIntroductoryOfferStore(tmp_path / "offers.sqlite")

    class VerifiedRegistrations:
        def get(self, user_id):
            from mcm_solarcheck.services.registration import OnlineRegistration
            return OnlineRegistration(
                user_id,
                "Customer",
                "customer@example.com",
            ).verify(datetime(2026, 10, 1, tzinfo=timezone.utc))

    checkout, payments, gateway = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
        introductory_offers=offers,
        registrations=VerifiedRegistrations(),
    )

    def fail_authorize(*args, **kwargs):
        raise RuntimeError("provider authorization failed")

    checkout._authorization.authorize = fail_authorize

    with pytest.raises(RuntimeError, match="provider authorization failed"):
        checkout.checkout(
            "payment-failed-intro",
            user_id="user-failed-intro",
            project_id="project-a",
            job_id="job-failed-intro",
            plant_kwp=750,
            method=PaymentMethod.CARD,
            provider_id="provider-a",
            merchant_account_id="merchant-a",
            now=datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc),
        )

    assert offers.has_used("user-failed-intro") is False
    assert offers.reserve(
        "user-failed-intro",
        "payment-retry-intro",
        policy_version=1,
        now=datetime(2026, 10, 6, 10, 1, tzinfo=timezone.utc),
    ) is True


def test_failed_card_merchant_binding_releases_introductory_offer(tmp_path) -> None:
    offers = SQLiteIntroductoryOfferStore(tmp_path / "offers-bind.sqlite")

    class VerifiedRegistrations:
        def get(self, user_id):
            from mcm_solarcheck.services.registration import OnlineRegistration
            return OnlineRegistration(user_id, "Customer", "customer@example.com").verify(
                datetime(2026, 10, 1, tzinfo=timezone.utc)
            )

    checkout, _, _ = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
        introductory_offers=offers,
        registrations=VerifiedRegistrations(),
    )

    with pytest.raises(KeyError):
        checkout.checkout(
            "payment-bind-failure",
            user_id="user-bind-failure",
            project_id="project-a",
            job_id="job-a",
            plant_kwp=750,
            method=PaymentMethod.CARD,
            provider_id="provider-a",
            merchant_account_id="missing-merchant",
            now=datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc),
        )

    assert offers.reserve(
        "user-bind-failure",
        "payment-bind-retry",
        policy_version=1,
        now=datetime(2026, 10, 6, 10, 1, tzinfo=timezone.utc),
    )


def test_failed_card_snapshot_binding_releases_introductory_offer(tmp_path) -> None:
    offers = SQLiteIntroductoryOfferStore(tmp_path / "offers-snapshot.sqlite")

    class VerifiedRegistrations:
        def get(self, user_id):
            from mcm_solarcheck.services.registration import OnlineRegistration
            return OnlineRegistration(user_id, "Customer", "customer@example.com").verify(
                datetime(2026, 10, 1, tzinfo=timezone.utc)
            )

    checkout, _, _ = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
        introductory_offers=offers,
        registrations=VerifiedRegistrations(),
    )

    def fail_snapshot(*args, **kwargs):
        raise RuntimeError("snapshot binding failed")

    checkout._payments.bind_processing_snapshot = fail_snapshot

    with pytest.raises(RuntimeError, match="snapshot binding failed"):
        checkout.checkout(
            "payment-snapshot-failure",
            user_id="user-snapshot-failure",
            project_id="project-a",
            job_id="job-a",
            plant_kwp=750,
            method=PaymentMethod.CARD,
            provider_id="provider-a",
            merchant_account_id="merchant-a",
            now=datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc),
        )

    assert offers.reserve(
        "user-snapshot-failure",
        "payment-snapshot-retry",
        policy_version=1,
        now=datetime(2026, 10, 6, 10, 1, tzinfo=timezone.utc),
    )


def test_card_checkout_retry_keeps_introductory_price(tmp_path) -> None:
    offers = SQLiteIntroductoryOfferStore(tmp_path / "offers-checkout-retry.sqlite")

    class VerifiedRegistrations:
        def get(self, user_id):
            from mcm_solarcheck.services.registration import OnlineRegistration
            return OnlineRegistration(user_id, "Customer", "customer@example.com").verify(
                datetime(2026, 10, 1, tzinfo=timezone.utc)
            )

    checkout, _, _ = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
        introductory_offers=offers,
        registrations=VerifiedRegistrations(),
    )
    now = datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc)
    assert offers.reserve("user-retry", "payment-retry", policy_version=1, now=now)

    result = checkout.checkout(
        "payment-retry",
        user_id="user-retry",
        project_id="project-a",
        job_id="job-a",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-a",
        now=now,
    )

    assert result.amount == PaymentAmount(5900, "EUR")


def test_failed_card_retry_releases_existing_same_payment_reservation(tmp_path) -> None:
    offers = SQLiteIntroductoryOfferStore(tmp_path / "offers-failed-retry.sqlite")

    class VerifiedRegistrations:
        def get(self, user_id):
            from mcm_solarcheck.services.registration import OnlineRegistration
            return OnlineRegistration(user_id, "Customer", "customer@example.com").verify(
                datetime(2026, 10, 1, tzinfo=timezone.utc)
            )

    checkout, _, _ = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
        introductory_offers=offers,
        registrations=VerifiedRegistrations(),
    )
    now = datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc)
    assert offers.reserve("user-failed-retry", "payment-failed-retry", policy_version=1, now=now)

    def fail_authorize(*args, **kwargs):
        raise RuntimeError("provider retry failed")

    checkout._authorization.authorize = fail_authorize

    with pytest.raises(RuntimeError, match="provider retry failed"):
        checkout.checkout(
            "payment-failed-retry",
            user_id="user-failed-retry",
            project_id="project-a",
            job_id="job-a",
            plant_kwp=750,
            method=PaymentMethod.CARD,
            provider_id="provider-a",
            merchant_account_id="merchant-a",
            now=now,
        )

    assert offers.reserve(
        "user-failed-retry", "payment-after-failed-retry", policy_version=1, now=now
    )


def test_card_checkout_retry_keeps_reserved_offer_after_deadline(tmp_path) -> None:
    offers = SQLiteIntroductoryOfferStore(tmp_path / "offers-deadline-retry.sqlite")

    class Registrations:
        def get(self, user_id):
            raise AssertionError("existing reservation must not recheck registration")

    checkout, _, _ = build_checkout(
        tmp_path,
        PaymentMethod.CARD,
        MerchantAccountKind.CARD_PROCESSOR,
        introductory_offers=offers,
        registrations=Registrations(),
    )
    reserved_at = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    assert offers.reserve(
        "user-deadline-retry", "payment-deadline-retry", policy_version=1, now=reserved_at
    )

    result = checkout.checkout(
        "payment-deadline-retry",
        user_id="user-deadline-retry",
        project_id="project-a",
        job_id="job-a",
        plant_kwp=750,
        method=PaymentMethod.CARD,
        provider_id="provider-a",
        merchant_account_id="merchant-a",
        now=datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc),
    )

    assert result.amount == PaymentAmount(5900, "EUR")
