"""SQLite persistence for SolarCheck Online password credentials."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.online_credentials import PasswordCredential


class SQLiteCredentialStore:
    """Persist salted password derivations without plaintext credentials."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS online_credentials (
                    user_id TEXT PRIMARY KEY,
                    salt_hex TEXT NOT NULL,
                    digest_hex TEXT NOT NULL,
                    iterations INTEGER NOT NULL CHECK (iterations > 0)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def save(self, credential: PasswordCredential) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO online_credentials (
                    user_id, salt_hex, digest_hex, iterations
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    salt_hex = excluded.salt_hex,
                    digest_hex = excluded.digest_hex,
                    iterations = excluded.iterations
                """,
                (
                    credential.user_id,
                    credential.salt_hex,
                    credential.digest_hex,
                    credential.iterations,
                ),
            )

    def get(self, user_id: str) -> PasswordCredential:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT salt_hex, digest_hex, iterations
                FROM online_credentials
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            raise KeyError(user_id)
        return PasswordCredential(user_id, row[0], row[1], row[2])
