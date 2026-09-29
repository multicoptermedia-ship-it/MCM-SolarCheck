from mcm_solarcheck.services.payment_methods import (
    PaymentMethod,
    payment_method_capabilities,
)


def test_sepa_direct_debit_has_mandate_flow() -> None:
    item = payment_method_capabilities(PaymentMethod.SEPA_DIRECT_DEBIT)
    assert item.requires_mandate is True
    assert item.supports_authorize_capture is False
    assert item.supports_void is False


def test_paypal_and_card_support_deferred_capture() -> None:
    for method in (PaymentMethod.PAYPAL, PaymentMethod.CARD):
        item = payment_method_capabilities(method)
        assert item.requires_mandate is False
        assert item.supports_authorize_capture is True
        assert item.supports_void is True
