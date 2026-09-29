"""SQLite persistence for provider-neutral SEPA mandates."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.sepa import SepaMandate, SepaMandateStatus


class SQLiteSepaMandateStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sepa_mandates (
                    mandate_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    provider_reference TEXT,
                    status TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def create(self, mandate: SepaMandate) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sepa_mandates (
                    mandate_id, user_id, provider_id,
                    provider_reference, status
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    mandate.mandate_id,
                    mandate.user_id,
                    mandate.provider_id,
                    mandate.provider_reference,
                    mandate.status.value,
                ),
            )

    def get(self, mandate_id: str) -> SepaMandate:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT user_id, provider_id, provider_reference, status
                FROM sepa_mandates
                WHERE mandate_id = ?
                """,
                (mandate_id,),
            ).fetchone()
        if row is None:
            raise KeyError(mandate_id)
        return SepaMandate(
            mandate_id,
            row[0],
            row[1],
            row[2],
            SepaMandateStatus(row[3]),
        )

    def activate(
        self, mandate_id: str, user_id: str, provider_reference: str
    ) -> SepaMandate:
        return self._transition(
            mandate_id,
            user_id,
            lambda mandate: mandate.activate(provider_reference),
        )

    def revoke(self, mandate_id: str, user_id: str) -> SepaMandate:
        return self._transition(
            mandate_id,
            user_id,
            lambda mandate: mandate.revoke(),
        )

    def _transition(self, mandate_id, user_id, transition):
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT user_id, provider_id, provider_reference, status
                FROM sepa_mandates
                WHERE mandate_id = ?
                """,
                (mandate_id,),
            ).fetchone()
            if row is None:
                raise KeyError(mandate_id)
            if row[0] != user_id:
                raise PermissionError("SEPA mandate ownership mismatch")

            current = SepaMandate(
                mandate_id,
                row[0],
                row[1],
                row[2],
                SepaMandateStatus(row[3]),
            )
            updated = transition(current)
            connection.execute(
                """
                UPDATE sepa_mandates
                SET provider_reference = ?, status = ?
                WHERE mandate_id = ?
                """,
                (
                    updated.provider_reference,
                    updated.status.value,
                    mandate_id,
                ),
            )
            connection.commit()
            return updated
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
