from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcm_solarcheck.services.online_session import (
    InMemorySessionStore,
    OnlineSessionService,
)


def test_session_roundtrip_resolves_authenticated_user() -> None:
    now = datetime(2026, 10, 3, 19, 0, tzinfo=timezone.utc)
    service = OnlineSessionService(InMemorySessionStore(), now=lambda: now)

    session = service.create("user-1")

    assert session.user_id == "user-1"
    assert session.token
    assert service.require_user(session.token) == "user-1"


def test_unknown_session_fails_closed() -> None:
    service = OnlineSessionService(InMemorySessionStore())

    with pytest.raises(PermissionError, match="online session is invalid"):
        service.require_user("unknown-session-token")


def test_expired_session_is_deleted_and_rejected() -> None:
    clock = [datetime(2026, 10, 3, 19, 0, tzinfo=timezone.utc)]
    store = InMemorySessionStore()
    service = OnlineSessionService(
        store,
        duration=timedelta(minutes=30),
        now=lambda: clock[0],
    )
    session = service.create("user-1")
    clock[0] += timedelta(minutes=31)

    with pytest.raises(PermissionError, match="online session is invalid"):
        service.require_user(session.token)
    with pytest.raises(KeyError):
        store.get(session.token)


def test_revoked_session_cannot_be_reused() -> None:
    service = OnlineSessionService(InMemorySessionStore())
    session = service.create("user-1")

    service.revoke(session.token)

    with pytest.raises(PermissionError, match="online session is invalid"):
        service.require_user(session.token)


def test_session_rejects_non_utc_clock() -> None:
    service = OnlineSessionService(
        InMemorySessionStore(),
        now=lambda: datetime(2026, 10, 3, 19, 0),
    )

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        service.create("user-1")
