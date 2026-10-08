"""End-to-end checkout orchestration for payable online SolarCheck orders."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from mcm_solarcheck.services.billing import ComputeJobBillingStore

from mcm_solarcheck.services.introductory_offer import IntroductoryOfferPolicy, IntroductoryOfferStore, has_verified_registration
from mcm_solarcheck.services.merchant_binding import MerchantAccountBindingService
from mcm_solarcheck.services.payment import OnlinePayment, PaymentStatus
from mcm_solarcheck.services.payment_gateway import PaymentAuthorizationService
from mcm_solarcheck.services.payment_methods import (
    PaymentMethod,
    payment_method_capabilities,
)
from mcm_solarcheck.services.payment_pricing import PaymentPricingService
from mcm_solarcheck.services.payment_provider import PaymentProviderRegistry
from mcm_solarcheck.services.solarcheck_tariff import SolarCheckTariff, quote_solarcheck


class SolarCheckTariffStore(Protocol):
    def current(self, at: datetime) -> SolarCheckTariff:
        ...


class PaymentProcessingSnapshotStore(Protocol):
    def bind_processing_snapshot(
        self,
        payment_id: str,
        user_id: str,
        project_id: str,
        *,
        method: PaymentMethod,
        merchant_account_id: str,
        merchant_account_version: int,
        provider_id: str,
    ) -> OnlinePayment:
        ...


class OnlinePaymentCheckoutService:
    """Create, bind and authorize one online payment in server-owned order."""

    def __init__(
        self,
        pricing: PaymentPricingService,
        merchants: MerchantAccountBindingService,
        providers: PaymentProviderRegistry,
        authorization: PaymentAuthorizationService,
        payments: PaymentProcessingSnapshotStore,
        tariffs: SolarCheckTariffStore,
        billing: ComputeJobBillingStore | None = None,
        introductory_offers: IntroductoryOfferStore | None = None,
        introductory_offer_policy: IntroductoryOfferPolicy = IntroductoryOfferPolicy(),
        registrations=None,
    ) -> None:
        self._pricing = pricing
        self._merchants = merchants
        self._providers = providers
        self._authorization = authorization
        self._payments = payments
        self._tariffs = tariffs
        self._billing = billing
        self._introductory_offers = introductory_offers
        self._introductory_offer_policy = introductory_offer_policy
        self._registrations = registrations

    def checkout(
        self,
        payment_id: str,
        *,
        user_id: str,
        project_id: str,
        job_id: str,
        plant_kwp: int,
        method: PaymentMethod,
        provider_id: str,
        merchant_account_id: str,
        now: datetime,
        voucher_code: str | None = None,
    ) -> OnlinePayment:
        if self._billing is not None:
            try:
                billing = self._billing.get(job_id)
            except KeyError as exc:
                raise ValueError("checkout requires completed compute job billing") from exc
            if (
                billing.delivery.user_id != user_id
                or billing.delivery.project_id != project_id
            ):
                raise PermissionError("checkout billing ownership mismatch")

        if not isinstance(method, PaymentMethod):
            raise ValueError("payment method must be a PaymentMethod value")
        provider = self._providers.get(provider_id)
        provider.require(method)
        capabilities = payment_method_capabilities(method)
        if not capabilities.supports_authorize_capture:
            raise ValueError(
                f"payment method {method.value} requires its dedicated processing flow"
            )

        tariff = self._tariffs.current(now)
        quote = quote_solarcheck(tariff, plant_kwp=plant_kwp, quoted_at=now)

        offer_reserved = False
        base_amount = quote.amount
        if self._introductory_offers is not None:
            offer_reserved = self._introductory_offers.is_reserved(
                user_id,
                payment_id,
                policy_version=self._introductory_offer_policy.version,
            )
            if (
                not offer_reserved
                and self._introductory_offer_policy.is_available_at(now)
            ):
                if self._registrations is None:
                    raise RuntimeError("introductory offer requires registration authority")
                if has_verified_registration(self._registrations, user_id):
                    offer_reserved = self._introductory_offers.reserve(
                        user_id,
                        payment_id,
                        policy_version=self._introductory_offer_policy.version,
                        now=now,
                    )
            if offer_reserved:
                base_amount = self._introductory_offer_policy.amount

        try:
            payment = self._pricing.create_payment(
            payment_id,
            user_id=user_id,
            project_id=project_id,
            job_id=job_id,
            base_amount=base_amount,
            now=now,
            voucher_code=voucher_code,
            tariff_version=quote.tariff_version,
            plant_kwp=quote.plant_kwp,
            )
        except Exception:
            if offer_reserved:
                self._introductory_offers.release(user_id, payment_id)
            raise
        if payment.status is PaymentStatus.SETTLED:
            return payment

        proposed = OnlinePayment(
            payment.payment_id,
            payment.user_id,
            payment.project_id,
            payment.job_id,
            payment.amount,
            payment.status,
            payment.provider_reference,
            method,
            tariff_version=payment.tariff_version,
            plant_kwp=payment.plant_kwp,
        )
        try:
            bound = self._merchants.bind(
                proposed,
                merchant_account_id,
                provider_id=provider.provider_id,
            )

            self._payments.bind_processing_snapshot(
                payment.payment_id,
                user_id,
                project_id,
                method=method,
                merchant_account_id=bound.merchant_account_id,
                merchant_account_version=bound.merchant_account_version,
                provider_id=bound.provider_id,
            )
            return self._authorization.authorize(
                payment.payment_id,
                user_id=user_id,
                project_id=project_id,
            )
        except Exception:
            if offer_reserved:
                self._introductory_offers.release(user_id, payment_id)
            raise
