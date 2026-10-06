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
