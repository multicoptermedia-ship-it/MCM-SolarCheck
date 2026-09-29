"""Persistent replay guard for authenticated payment provider events."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLitePaymentWebhookReplayStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_webhook_events (
                    provider_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    processed INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (provider_id, event_id)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def reserve(self, provider_id: str, event_id: str) -> bool:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT processed
                FROM payment_webhook_events
                WHERE provider_id = ? AND event_id = ?
                """,
                (provider_id, event_id),
            ).fetchone()
            if row is not None:
                connection.commit()
                return False
            connection.execute(
                """
                INSERT INTO payment_webhook_events (
                    provider_id, event_id, processed
                ) VALUES (?, ?, 0)
                """,
                (provider_id, event_id),
            )
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_processed(self, provider_id: str, event_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE payment_webhook_events
                SET processed = 1
                WHERE provider_id = ? AND event_id = ?
                """,
                (provider_id, event_id),
            )
            if cursor.rowcount != 1:
                raise KeyError((provider_id, event_id))

    def release(self, provider_id: str, event_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM payment_webhook_events
                WHERE provider_id = ? AND event_id = ? AND processed = 0
                """,
                (provider_id, event_id),
            )

    def is_processed(self, provider_id: str, event_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT processed
                FROM payment_webhook_events
                WHERE provider_id = ? AND event_id = ?
                """,
                (provider_id, event_id),
            ).fetchone()
        return bool(row and row[0])
