import pytest

from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.payment_provider import (
    PaymentProviderCapabilities,
    PaymentProviderRegistry,
)
from mcm_solarcheck.services.payment_routing import PaymentProviderRoutingService


def payment(method: PaymentMethod | None) -> OnlinePayment:
    return OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
        method=method,
    )


def routing() -> PaymentProviderRoutingService:
    return PaymentProviderRoutingService(
        PaymentProviderRegistry(
            (
                PaymentProviderCapabilities(
                    "provider-card",
                    frozenset({PaymentMethod.CARD}),
                ),
                PaymentProviderCapabilities(
                    "provider-paypal",
                    frozenset({PaymentMethod.PAYPAL}),
                ),
                PaymentProviderCapabilities(
                    "provider-sepa",
                    frozenset({PaymentMethod.SEPA_DIRECT_DEBIT}),
                ),
            )
        )
    )


def test_selected_method_must_match_provider() -> None:
    service = routing()
    service.require_provider(payment(PaymentMethod.PAYPAL), "provider-paypal")

    with pytest.raises(ValueError, match="does not support"):
        service.require_provider(payment(PaymentMethod.PAYPAL), "provider-card")


def test_missing_method_cannot_reach_provider() -> None:
    with pytest.raises(ValueError, match="must be selected"):
        routing().require_provider(payment(None), "provider-card")


def test_sepa_uses_distinct_processing_flow() -> None:
    with pytest.raises(ValueError, match="distinct processing flow"):
        routing().require_provider(
            payment(PaymentMethod.SEPA_DIRECT_DEBIT),
            "provider-sepa",
        )


def test_bound_payment_cannot_be_routed_to_different_provider() -> None:
    bound = OnlinePayment(
        "payment-bound",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
        method=PaymentMethod.PAYPAL,
        provider_id="provider-paypal",
    )

    routing().require_provider(bound, "provider-paypal")

    with pytest.raises(ValueError, match="provider snapshot mismatch"):
        routing().require_provider(bound, "provider-card")


@pytest.mark.parametrize("provider_id", ["", "   ", None, 123])
def test_provider_lookup_rejects_invalid_identity(provider_id) -> None:
    with pytest.raises(ValueError, match="provider_id"):
        routing().require_provider(payment(PaymentMethod.CARD), provider_id)
