"""SQLite persistence for online registration and email verification."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

from mcm_solarcheck.services.registration import OnlineRegistration, RegistrationStatus


class SQLiteOnlineRegistrationStore:
    """Persist registrations and one-time verification token digests."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS online_registrations (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verified_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS email_verifications (
                    token_digest TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES online_registrations(user_id)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def create(
        self,
        registration: OnlineRegistration,
        *,
        token: str,
        expires_at: datetime,
    ) -> None:
        digest = _digest(token)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO online_registrations (
                    user_id, display_name, email, status, verified_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    registration.user_id,
                    registration.display_name,
                    registration.email,
                    registration.status.value,
                    None,
                ),
            )
            connection.execute(
                """
                INSERT INTO email_verifications (
                    token_digest, user_id, expires_at, consumed_at
                ) VALUES (?, ?, ?, NULL)
                """,
                (digest, registration.user_id, expires_at.isoformat()),
            )

    def get(self, user_id: str) -> OnlineRegistration:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT display_name, email, status, verified_at
                FROM online_registrations
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            raise KeyError(user_id)
        return OnlineRegistration(
            user_id,
            row[0],
            row[1],
            RegistrationStatus(row[2]),
            datetime.fromisoformat(row[3]) if row[3] is not None else None,
        )

    def verify(self, token: str, *, now: datetime) -> OnlineRegistration:
        """Consume one unexpired token and verify its registration atomically."""
        digest = _digest(token)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT user_id, expires_at, consumed_at
                FROM email_verifications
                WHERE token_digest = ?
                """,
                (digest,),
            ).fetchone()
            if row is None:
                raise PermissionError("invalid email verification token")
            if row[2] is not None:
                raise PermissionError("email verification token already consumed")
            if now.isoformat() >= row[1]:
                raise PermissionError("email verification token expired")

            registration_row = connection.execute(
                """
                SELECT display_name, email, status, verified_at
                FROM online_registrations
                WHERE user_id = ?
                """,
                (row[0],),
            ).fetchone()
            if registration_row is None:
                raise KeyError(row[0])
            registration = OnlineRegistration(
                row[0],
                registration_row[0],
                registration_row[1],
                RegistrationStatus(registration_row[2]),
                (
                    datetime.fromisoformat(registration_row[3])
                    if registration_row[3] is not None
                    else None
                ),
            )
            verified = registration.verify(now)
            connection.execute(
                """
                UPDATE online_registrations
                SET status = ?, verified_at = ?
                WHERE user_id = ?
                """,
                (
                    verified.status.value,
                    verified.verified_at.isoformat(),
                    verified.user_id,
                ),
            )
            connection.execute(
                """
                UPDATE email_verifications
                SET consumed_at = ?
                WHERE token_digest = ?
                """,
                (now.isoformat(), digest),
            )
            connection.commit()
            return verified
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def _digest(token: str) -> str:
    if not isinstance(token, str) or not token.strip():
        raise ValueError("verification token must be non-empty")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
