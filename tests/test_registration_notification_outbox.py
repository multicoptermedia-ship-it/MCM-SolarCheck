from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.infrastructure.sqlite_registration import (
    SQLiteOnlineRegistrationStore,
)
from mcm_solarcheck.services.registration import OnlineRegistration


def test_verification_persists_notification_outbox_atomically(tmp_path) -> None:
    database = tmp_path / "registration.sqlite"
    store = SQLiteOnlineRegistrationStore(database)
    start = datetime(2026, 9, 29, 13, 0, tzinfo=timezone.utc)
    store.create(
        OnlineRegistration("user-a", "MCM Dronetech", "user@example.com"),
        token="secret-token",
        expires_at=start + timedelta(minutes=30),
    )

    store.verify("secret-token", now=start + timedelta(minutes=1))

    reopened = SQLiteOnlineRegistrationStore(database)
    assert reopened.pending_notification_user_ids() == ["user-a"]

    reopened.mark_notification_sent(
        "user-a", now=start + timedelta(minutes=2)
    )
    assert reopened.pending_notification_user_ids() == []
    with pytest.raises(KeyError):
        reopened.mark_notification_sent(
            "user-a", now=start + timedelta(minutes=3)
        )


def test_failed_verification_does_not_create_notification_outbox(tmp_path) -> None:
    store = SQLiteOnlineRegistrationStore(tmp_path / "registration.sqlite")
    start = datetime(2026, 9, 29, 13, 0, tzinfo=timezone.utc)
    store.create(
        OnlineRegistration("user-a", "MCM Dronetech", "user@example.com"),
        token="secret-token",
        expires_at=start + timedelta(minutes=30),
    )

    with pytest.raises(PermissionError):
        store.verify("wrong-token", now=start + timedelta(minutes=1))

    assert store.pending_notification_user_ids() == []
