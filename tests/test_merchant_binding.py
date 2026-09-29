import pytest

from mcm_solarcheck.infrastructure.sqlite_merchant_account import (
    SQLiteMerchantAccountStore,
)
from mcm_solarcheck.services.merchant_account import (
    MerchantAccount,
    MerchantAccountKind,
)
from mcm_solarcheck.services.merchant_binding import MerchantAccountBindingService
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
from mcm_solarcheck.services.payment_methods import PaymentMethod


def test_new_payments_bind_current_account_version(tmp_path) -> None:
    accounts = SQLiteMerchantAccountStore(tmp_path / "merchant.sqlite")
    first = MerchantAccount(
        "paypal-main",
        "paypal",
        MerchantAccountKind.PAYPAL,
        "old@example.invalid",
    )
    accounts.save(first)
    accounts.save(
        first.supersede(display_reference="new@example.invalid")
    )

    payment = OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
        method=PaymentMethod.PAYPAL,
    )
    bound = MerchantAccountBindingService(accounts).bind(
        payment, "paypal-main"
    )

    assert bound.merchant_account_id == "paypal-main"
    assert bound.provider_id == "paypal"
    assert bound.merchant_account_version == 2
    assert bound.provider_id == "paypal"
    assert payment.merchant_account_id is None


@pytest.mark.parametrize(
    ("method", "kind"),
    [
        (PaymentMethod.SEPA_DIRECT_DEBIT, MerchantAccountKind.PAYPAL),
        (PaymentMethod.PAYPAL, MerchantAccountKind.BANK),
        (PaymentMethod.CARD, MerchantAccountKind.PAYPAL),
    ],
)
def test_binding_rejects_account_kind_for_other_payment_method(
    tmp_path, method, kind
) -> None:
    accounts = SQLiteMerchantAccountStore(tmp_path / "merchant.sqlite")
    accounts.save(
        MerchantAccount(
            "wrong-account",
            "provider-a",
            kind,
            "masked-reference",
        )
    )
    payment = OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
        method=method,
    )

    with pytest.raises(ValueError, match="kind does not match"):
        MerchantAccountBindingService(accounts).bind(
            payment, "wrong-account"
        )


def test_binding_requires_explicit_payment_method(tmp_path) -> None:
    accounts = SQLiteMerchantAccountStore(tmp_path / "merchant.sqlite")
    accounts.save(
        MerchantAccount(
            "paypal-main",
            "paypal",
            MerchantAccountKind.PAYPAL,
            "merchant@example.invalid",
        )
    )
    payment = OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
    )

    with pytest.raises(ValueError, match="payment method is required"):
        MerchantAccountBindingService(accounts).bind(
            payment, "paypal-main"
        )


def test_binding_rejects_account_from_other_routed_provider(tmp_path) -> None:
    accounts = SQLiteMerchantAccountStore(tmp_path / "merchant.sqlite")
    accounts.save(
        MerchantAccount(
            "paypal-main",
            "provider-a",
            MerchantAccountKind.PAYPAL,
            "merchant@example.invalid",
        )
    )
    payment = OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
        method=PaymentMethod.PAYPAL,
    )

    with pytest.raises(ValueError, match="provider mismatch"):
        MerchantAccountBindingService(accounts).bind(
            payment,
            "paypal-main",
            provider_id="provider-b",
        )


def test_binding_accepts_account_for_routed_provider(tmp_path) -> None:
    accounts = SQLiteMerchantAccountStore(tmp_path / "merchant.sqlite")
    accounts.save(
        MerchantAccount(
            "paypal-main",
            "provider-a",
            MerchantAccountKind.PAYPAL,
            "merchant@example.invalid",
        )
    )
    payment = OnlinePayment(
        "payment-a",
        "user-a",
        "project-a",
        "job-a",
        PaymentAmount(12900, "EUR"),
        method=PaymentMethod.PAYPAL,
    )

    bound = MerchantAccountBindingService(accounts).bind(
        payment,
        "paypal-main",
        provider_id="provider-a",
    )

    assert bound.merchant_account_id == "paypal-main"
