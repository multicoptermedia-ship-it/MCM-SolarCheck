"""Provider selection gate for a chosen payment method."""

from __future__ import annotations

from mcm_solarcheck.services.payment import OnlinePayment
from mcm_solarcheck.services.payment_methods import payment_method_capabilities
from mcm_solarcheck.services.payment_provider import PaymentProviderRegistry


class PaymentProviderRoutingService:
    def __init__(self, providers: PaymentProviderRegistry) -> None:
        self._providers = providers

    def require_provider(
        self, payment: OnlinePayment, provider_id: str
    ) -> None:
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id must be non-empty")
        provider_id = provider_id.strip()
        if payment.provider_id is not None and payment.provider_id != provider_id:
            raise ValueError("payment provider snapshot mismatch")
        if payment.method is None:
            raise ValueError("payment method must be selected before provider routing")

        method = payment_method_capabilities(payment.method)
        if not method.supports_authorize_capture:
            raise ValueError(
                f"payment method {payment.method.value} requires a distinct processing flow"
            )

        provider = self._providers.get(provider_id)
        provider.require(payment.method)
