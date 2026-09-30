"""End-to-end checkout orchestration for payable online SolarCheck orders."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from mcm_solarcheck.services.merchant_binding import MerchantAccountBindingService
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount, PaymentStatus
from mcm_solarcheck.services.payment_gateway import PaymentAuthorizationService
from mcm_solarcheck.services.payment_methods import (
    PaymentMethod,
    payment_method_capabilities,
)
from mcm_solarcheck.services.payment_pricing import PaymentPricingService
from mcm_solarcheck.services.payment_provider import PaymentProviderRegistry


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
    ) -> None:
        self._pricing = pricing
        self._merchants = merchants
        self._providers = providers
        self._authorization = authorization
        self._payments = payments

    def checkout(
        self,
        payment_id: str,
        *,
        user_id: str,
        project_id: str,
        job_id: str,
        base_amount: PaymentAmount,
        method: PaymentMethod,
        provider_id: str,
        merchant_account_id: str,
        now: datetime,
        voucher_code: str | None = None,
    ) -> OnlinePayment:
        if not isinstance(method, PaymentMethod):
            raise ValueError("payment method must be a PaymentMethod value")
        provider = self._providers.get(provider_id)
        provider.require(method)

        payment = self._pricing.create_payment(
            payment_id,
            user_id=user_id,
            project_id=project_id,
            job_id=job_id,
            base_amount=base_amount,
            now=now,
            voucher_code=voucher_code,
        )
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
        )
        bound = self._merchants.bind(
            proposed,
            merchant_account_id,
            provider_id=provider.provider_id,
        )

        capabilities = payment_method_capabilities(method)
        if not capabilities.supports_authorize_capture:
            raise ValueError(
                f"payment method {method.value} requires its dedicated processing flow"
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
