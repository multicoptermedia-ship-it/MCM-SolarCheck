from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from mcm_solarcheck.infrastructure.sqlite_session import SQLiteSessionStore
from mcm_solarcheck.services.online_session import OnlineSessionService


def test_sqlite_session_survives_service_recomposition(tmp_path) -> None:
    database = tmp_path / "online.sqlite"
    now = datetime(2026, 10, 3, 20, 0, tzinfo=timezone.utc)

    first = OnlineSessionService(SQLiteSessionStore(database), now=lambda: now)
    session = first.create("user-1")

    second = OnlineSessionService(SQLiteSessionStore(database), now=lambda: now)
    assert second.require_user(session.token) == "user-1"


def test_sqlite_session_expiry_is_persisted_and_enforced(tmp_path) -> None:
    database = tmp_path / "online.sqlite"
    clock = [datetime(2026, 10, 3, 20, 0, tzinfo=timezone.utc)]
    service = OnlineSessionService(
        SQLiteSessionStore(database),
        duration=timedelta(minutes=5),
        now=lambda: clock[0],
    )
    session = service.create("user-1")
    clock[0] += timedelta(minutes=6)

    with pytest.raises(PermissionError, match="online session is invalid"):
        service.require_user(session.token)

    with pytest.raises(KeyError):
        SQLiteSessionStore(database).get(session.token)


def test_sqlite_session_revoke_is_durable(tmp_path) -> None:
    database = tmp_path / "online.sqlite"
    service = OnlineSessionService(SQLiteSessionStore(database))
    session = service.create("user-1")

    service.revoke(session.token)

    with pytest.raises(KeyError):
        SQLiteSessionStore(database).get(session.token)


def test_sqlite_session_does_not_persist_bearer_token(tmp_path) -> None:
    database = tmp_path / "online.sqlite"
    service = OnlineSessionService(SQLiteSessionStore(database))
    session = service.create("user-1")

    with sqlite3.connect(database) as connection:
        stored_token = connection.execute(
            "SELECT token FROM online_sessions WHERE user_id = ?",
            ("user-1",),
        ).fetchone()[0]

    assert stored_token != session.token
    assert session.token not in stored_token
    assert len(stored_token) == 64
    assert service.require_user(session.token) == "user-1"
