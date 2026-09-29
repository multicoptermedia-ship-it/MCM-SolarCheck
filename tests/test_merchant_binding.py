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
    assert bound.merchant_account_version == 2
    assert payment.merchant_account_id is None
