import pytest

from mcm_solarcheck.services.payment_methods import PaymentMethod
from mcm_solarcheck.services.payment_provider import (
    PaymentProviderCapabilities,
    PaymentProviderRegistry,
)


def test_provider_can_support_multiple_payment_methods() -> None:
    provider = PaymentProviderCapabilities(
        "provider-a",
        frozenset(
            {
                PaymentMethod.SEPA_DIRECT_DEBIT,
                PaymentMethod.CARD,
            }
        ),
    )

    assert provider.supports(PaymentMethod.SEPA_DIRECT_DEBIT)
    assert provider.supports(PaymentMethod.CARD)
    assert not provider.supports(PaymentMethod.PAYPAL)


def test_registry_allows_method_specific_provider_expansion() -> None:
    registry = PaymentProviderRegistry(
        (
            PaymentProviderCapabilities(
                "provider-a",
                frozenset(
                    {
                        PaymentMethod.SEPA_DIRECT_DEBIT,
                        PaymentMethod.CARD,
                    }
                ),
            ),
            PaymentProviderCapabilities(
                "provider-b",
                frozenset({PaymentMethod.PAYPAL}),
            ),
        )
    )

    assert [p.provider_id for p in registry.supporting(PaymentMethod.CARD)] == [
        "provider-a"
    ]
    assert [p.provider_id for p in registry.supporting(PaymentMethod.PAYPAL)] == [
        "provider-b"
    ]


def test_provider_rejects_unsupported_method() -> None:
    provider = PaymentProviderCapabilities(
        "provider-a", frozenset({PaymentMethod.CARD})
    )

    with pytest.raises(ValueError, match="does not support"):
        provider.require(PaymentMethod.SEPA_DIRECT_DEBIT)
