import pytest

from mcm_solarcheck.infrastructure.sqlite_merchant_account import (
    SQLiteMerchantAccountStore,
)
from mcm_solarcheck.services.merchant_account import (
    MerchantAccount,
    MerchantAccountKind,
)


def test_current_merchant_account_changes_without_rewriting_history(tmp_path) -> None:
    store = SQLiteMerchantAccountStore(tmp_path / "merchant.sqlite")
    first = MerchantAccount(
        "paypal-main",
        "paypal",
        MerchantAccountKind.PAYPAL,
        "old@example.invalid",
        credential_key="PAYPAL_V1",
    )
    store.save(first)
    second = first.supersede(
        display_reference="new@example.invalid",
        credential_key="PAYPAL_V2",
    )
    store.save(second)

    assert store.current("paypal-main") == second
    assert store.get("paypal-main", 1) == first
    assert store.get("paypal-main", 2) == second


def test_merchant_account_versions_cannot_skip_or_overwrite(tmp_path) -> None:
    store = SQLiteMerchantAccountStore(tmp_path / "merchant.sqlite")
    first = MerchantAccount(
        "bank-main",
        "sepa-provider",
        MerchantAccountKind.BANK,
        "DE**1234",
    )
    store.save(first)

    with pytest.raises(ValueError, match="not next"):
        store.save(first)

    skipped = MerchantAccount(
        "bank-main",
        "sepa-provider",
        MerchantAccountKind.BANK,
        "DE**9876",
        version=3,
    )
    with pytest.raises(ValueError, match="not next"):
        store.save(skipped)


def test_account_provider_cannot_change_across_versions(tmp_path) -> None:
    store = SQLiteMerchantAccountStore(tmp_path / "merchant.sqlite")
    store.save(
        MerchantAccount(
            "merchant-a",
            "provider-a",
            MerchantAccountKind.PAYPAL,
            "old-reference",
        )
    )

    with pytest.raises(ValueError, match="provider cannot change"):
        store.save(
            MerchantAccount(
                "merchant-a",
                "provider-b",
                MerchantAccountKind.PAYPAL,
                "new-reference",
                version=2,
            )
        )

    assert store.current("merchant-a").provider_id == "provider-a"


def test_account_kind_cannot_change_across_versions(tmp_path) -> None:
    store = SQLiteMerchantAccountStore(tmp_path / "merchant.sqlite")
    store.save(
        MerchantAccount(
            "merchant-a",
            "provider-a",
            MerchantAccountKind.PAYPAL,
            "old-reference",
        )
    )

    with pytest.raises(ValueError, match="kind cannot change"):
        store.save(
            MerchantAccount(
                "merchant-a",
                "provider-a",
                MerchantAccountKind.BANK,
                "new-reference",
                version=2,
            )
        )

    assert store.current("merchant-a").kind is MerchantAccountKind.PAYPAL
