from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest

from mcm_solarcheck.infrastructure.sqlite_registration import (
    SQLiteOnlineRegistrationStore,
)
from mcm_solarcheck.services.registration import OnlineRegistration, RegistrationStatus


def test_sqlite_registration_verifies_token_once(tmp_path) -> None:
    store = SQLiteOnlineRegistrationStore(tmp_path / "registration.sqlite")
    start = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
    store.create(
        OnlineRegistration("user-a", "MCM Dronetech", "User@Example.com"),
        token="secret-token",
        expires_at=start + timedelta(minutes=30),
    )

    verified = store.verify("secret-token", now=start + timedelta(minutes=1))

    assert verified.status is RegistrationStatus.VERIFIED
    assert verified.email == "user@example.com"
    assert store.get("user-a") == verified
    with pytest.raises(PermissionError, match="already consumed"):
        store.verify("secret-token", now=start + timedelta(minutes=2))


def test_sqlite_registration_rejects_expired_and_unknown_tokens(tmp_path) -> None:
    store = SQLiteOnlineRegistrationStore(tmp_path / "registration.sqlite")
    start = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
    store.create(
        OnlineRegistration("user-a", "MCM Dronetech", "user@example.com"),
        token="secret-token",
        expires_at=start + timedelta(minutes=30),
    )

    with pytest.raises(PermissionError, match="invalid"):
        store.verify("wrong-token", now=start + timedelta(minutes=1))
    with pytest.raises(PermissionError, match="expired"):
        store.verify("secret-token", now=start + timedelta(minutes=30))
    assert store.get("user-a").status is RegistrationStatus.PENDING


def test_sqlite_registration_token_is_single_use_under_concurrency(tmp_path) -> None:
    database = tmp_path / "registration.sqlite"
    store = SQLiteOnlineRegistrationStore(database)
    start = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
    store.create(
        OnlineRegistration("user-a", "MCM Dronetech", "user@example.com"),
        token="secret-token",
        expires_at=start + timedelta(minutes=30),
    )
    barrier = Barrier(2)

    def verify_once() -> str:
        local = SQLiteOnlineRegistrationStore(database)
        barrier.wait()
        try:
            local.verify("secret-token", now=start + timedelta(minutes=1))
            return "verified"
        except PermissionError as exc:
            assert "already consumed" in str(exc)
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: verify_once(), range(2)))

    assert sorted(results) == ["rejected", "verified"]
    assert store.get("user-a").status is RegistrationStatus.VERIFIED
