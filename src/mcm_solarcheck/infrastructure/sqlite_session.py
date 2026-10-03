"""SQLite persistence for SolarCheck Online server-side sessions."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from mcm_solarcheck.services.online_session import OnlineSession


class SQLiteSessionStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS online_sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def save(self, session: OnlineSession) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO online_sessions (token, user_id, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(token) DO UPDATE SET
                    user_id = excluded.user_id,
                    expires_at = excluded.expires_at
                """,
                (session.token, session.user_id, session.expires_at.isoformat()),
            )

    def get(self, token: str) -> OnlineSession:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT user_id, expires_at FROM online_sessions WHERE token = ?",
                (token,),
            ).fetchone()
        if row is None:
            raise KeyError(token)
        return OnlineSession(token, row[0], datetime.fromisoformat(row[1]))

    def delete(self, token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM online_sessions WHERE token = ?",
                (token,),
            )
