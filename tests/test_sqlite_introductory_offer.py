from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_introductory_offer import SQLiteIntroductoryOfferStore


def test_offer_usage_is_persisted_per_registered_user(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    assert store.has_used("user-a") is False
    store.mark_used("user-a", "payment-a", policy_version=1, used_at=now)
    assert store.has_used("user-a") is True

    with pytest.raises(ValueError, match="already used"):
        store.mark_used("user-a", "payment-b", policy_version=1, used_at=now)


def test_concurrent_offer_claims_allow_only_one_use(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    def claim(payment_id: str) -> bool:
        try:
            store.mark_used("user-a", payment_id, policy_version=1, used_at=now)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, ("payment-a", "payment-b")))

    assert sorted(results) == [False, True]
    assert store.has_used("user-a") is True


def test_released_offer_reservation_can_be_used_by_later_payment(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    assert store.reserve("user-a", "failed-payment", policy_version=1, now=now)
    assert store.has_used("user-a") is False
    assert not store.reserve("user-a", "parallel-payment", policy_version=1, now=now)

    store.release("user-a", "failed-payment")

    assert store.reserve("user-a", "successful-payment", policy_version=1, now=now)
    store.finalize("user-a", "successful-payment", used_at=now)
    assert store.has_used("user-a") is True


def test_offer_finalization_is_idempotent_only_for_same_payment(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)
    store.finalize("user-a", "payment-a", used_at=now)
    store.finalize("user-a", "payment-a", used_at=now)

    assert store.has_used("user-a") is True
    with pytest.raises(ValueError, match="payment mismatch"):
        store.finalize("user-a", "payment-b", used_at=now)


def test_same_payment_can_retry_offer_reservation(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers-retry.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)
    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)
    assert store.has_used("user-a") is False


def test_same_payment_retry_requires_same_offer_policy(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers-policy-retry.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)
    assert not store.reserve("user-a", "payment-a", policy_version=2, now=now)


def test_used_offer_is_not_reopened_by_same_payment_retry(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers-used-retry.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)
    store.finalize("user-a", "payment-a", used_at=now)

    assert not store.reserve("user-a", "payment-a", policy_version=1, now=now)
    assert store.has_used("user-a") is True


def test_release_does_not_delete_other_payment_reservation(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers-release-identity.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)
    store.release("user-a", "payment-b")

    assert not store.reserve("user-a", "payment-b", policy_version=1, now=now)
    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)


def test_release_does_not_reopen_used_offer(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers-release-used.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)
    store.finalize("user-a", "payment-a", used_at=now)
    store.release("user-a", "payment-a")

    assert store.has_used("user-a") is True
    assert not store.reserve("user-a", "payment-b", policy_version=1, now=now)


def test_released_same_payment_reservation_is_not_idempotent(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers-release-retry.sqlite")
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)
    store.release("user-a", "payment-a")

    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)


def test_reservation_lookup_requires_matching_payment_and_policy(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers-lookup.sqlite")
    now = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)

    assert store.is_reserved("user-a", "payment-a", policy_version=1)
    assert not store.is_reserved("user-a", "payment-b", policy_version=1)
    assert not store.is_reserved("user-a", "payment-a", policy_version=2)


def test_finalized_offer_is_not_reported_as_reserved(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers-lookup-used.sqlite")
    now = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)
    store.finalize("user-a", "payment-a", used_at=now)

    assert not store.is_reserved("user-a", "payment-a", policy_version=1)
    assert store.has_used("user-a")


def test_released_offer_is_not_reported_as_reserved(tmp_path) -> None:
    store = SQLiteIntroductoryOfferStore(tmp_path / "offers-lookup-released.sqlite")
    now = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    assert store.reserve("user-a", "payment-a", policy_version=1, now=now)
    store.release("user-a", "payment-a")

    assert not store.is_reserved("user-a", "payment-a", policy_version=1)
