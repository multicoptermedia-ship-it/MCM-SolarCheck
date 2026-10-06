"""Dedicated checkout orchestration for asynchronous SEPA payments."""

from __future__ import annotations

from datetime import datetime

from mcm_solarcheck.services.billing import ComputeJobBillingStore
from mcm_solarcheck.services.introductory_offer import IntroductoryOfferPolicy, IntroductoryOfferStore, has_verified_registration
from mcm_solarcheck.services.merchant_binding import MerchantAccountBindingService
from mcm_solarcheck.services.payment import OnlinePayment, PaymentStatus
from mcm_solarcheck.services.payment_checkout import (
    PaymentProcessingSnapshotStore,
    SolarCheckTariffStore,
)
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.payment_pricing import PaymentPricingService
from mcm_solarcheck.services.payment_provider import PaymentProviderRegistry
from mcm_solarcheck.services.solarcheck_tariff import quote_solarcheck


class OnlineSepaCheckoutService:
    """Price and bind SEPA without pretending it supports authorize/capture."""

    def __init__(
        self,
        pricing: PaymentPricingService,
        merchants: MerchantAccountBindingService,
        providers: PaymentProviderRegistry,
        payments: PaymentProcessingSnapshotStore,
        tariffs: SolarCheckTariffStore,
        billing: ComputeJobBillingStore,
        introductory_offers: IntroductoryOfferStore | None = None,
        introductory_offer_policy: IntroductoryOfferPolicy = IntroductoryOfferPolicy(),
        registrations=None,
    ) -> None:
        self._pricing = pricing
        self._merchants = merchants
        self._providers = providers
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
        provider_id: str,
        merchant_account_id: str,
        now: datetime,
        voucher_code: str | None = None,
    ) -> OnlinePayment:
        try:
            billing = self._billing.get(job_id)
        except KeyError as exc:
            raise ValueError("SEPA checkout requires completed compute job billing") from exc
        if (
            billing.delivery.user_id != user_id
            or billing.delivery.project_id != project_id
        ):
            raise PermissionError("SEPA checkout billing ownership mismatch")

        provider = self._providers.get(provider_id)
        provider.require(PaymentMethod.SEPA_DIRECT_DEBIT)

        existing_payment = None
        try:
            existing_payment = self._payments.get(payment_id)
        except KeyError:
            pass
        if existing_payment is not None:
            if (
                existing_payment.user_id != user_id
                or existing_payment.project_id != project_id
                or existing_payment.job_id != job_id
            ):
                raise PermissionError("SEPA checkout payment ownership mismatch")
            if existing_payment.plant_kwp != plant_kwp:
                raise ValueError("SEPA checkout plant size mismatch")
            if (
                existing_payment.merchant_account_id is not None
                and existing_payment.merchant_account_id != merchant_account_id
            ):
                raise ValueError("SEPA checkout merchant account mismatch")
            if existing_payment.provider_id is not None and existing_payment.provider_id != provider_id:
                raise ValueError("SEPA checkout provider mismatch")
            return existing_payment

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
            PaymentMethod.SEPA_DIRECT_DEBIT,
            tariff_version=payment.tariff_version,
            plant_kwp=payment.plant_kwp,
        )
        try:
            bound = self._merchants.bind(
                proposed,
                merchant_account_id,
                provider_id=provider.provider_id,
            )
            return self._payments.bind_processing_snapshot(
                payment.payment_id,
                user_id,
                project_id,
                method=PaymentMethod.SEPA_DIRECT_DEBIT,
                merchant_account_id=bound.merchant_account_id,
                merchant_account_version=bound.merchant_account_version,
                provider_id=bound.provider_id,
            )
        except Exception:
            if offer_reserved:
                self._introductory_offers.release(user_id, payment_id)
            raise
