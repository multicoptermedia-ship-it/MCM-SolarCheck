import pytest

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
        credential_key="env:PAYPAL_MAIN",
    )

    updated = current.supersede(
        display_reference="new-billing@example.invalid",
        credential_key="env:PAYPAL_NEW",
    )

    assert current.version == 1
    assert current.display_reference == "billing@example.invalid"
    assert updated.version == 2
    assert updated.display_reference == "new-billing@example.invalid"
    assert updated.credential_key == "env:PAYPAL_NEW"


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


def test_deactivate_and_reactivate_are_versioned_transitions() -> None:
    first = MerchantAccount(
        "merchant-a",
        "provider-a",
        MerchantAccountKind.PAYPAL,
        "masked-reference",
        credential_key="secret:paypal/a",
    )

    inactive = first.deactivate()
    assert inactive.version == 2
    assert inactive.active is False
    assert inactive.provider_id == first.provider_id
    assert inactive.kind is first.kind
    assert inactive.credential_key == first.credential_key
    assert first.active is True

    active_again = inactive.reactivate()
    assert active_again.version == 3
    assert active_again.active is True
    assert active_again.provider_id == first.provider_id
    assert active_again.kind is first.kind


def test_activation_transitions_reject_redundant_state() -> None:
    active = MerchantAccount(
        "merchant-a",
        "provider-a",
        MerchantAccountKind.BANK,
        "masked-reference",
    )
    with pytest.raises(ValueError, match="already active"):
        active.reactivate()

    inactive = active.deactivate()
    with pytest.raises(ValueError, match="already inactive"):
        inactive.deactivate()
