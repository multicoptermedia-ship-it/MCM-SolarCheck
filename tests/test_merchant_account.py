from mcm_solarcheck.services.merchant_account import (
    MerchantAccount,
    MerchantAccountKind,
)


def test_merchant_account_change_creates_new_version() -> None:
    current = MerchantAccount(
        "paypal-main",
        "paypal",
        MerchantAccountKind.PAYPAL,
        "billing@example.invalid",
        credential_key="PAYPAL_MAIN",
    )

    updated = current.supersede(
        display_reference="new-billing@example.invalid",
        credential_key="PAYPAL_NEW",
    )

    assert current.version == 1
    assert current.display_reference == "billing@example.invalid"
    assert updated.version == 2
    assert updated.display_reference == "new-billing@example.invalid"
    assert updated.credential_key == "PAYPAL_NEW"


def test_bank_account_reference_can_change_without_mutating_history() -> None:
    current = MerchantAccount(
        "bank-main",
        "sepa-provider",
        MerchantAccountKind.BANK,
        "DE** **** **** 1234",
    )

    updated = current.supersede(
        display_reference="DE** **** **** 9876"
    )

    assert current.display_reference.endswith("1234")
    assert updated.display_reference.endswith("9876")
    assert updated.version == current.version + 1
