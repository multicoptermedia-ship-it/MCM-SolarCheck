"""Persistent replay guard for authenticated payment provider events."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SQLitePaymentWebhookReplayStore:
    def __init__(self, database: str | Path, *, lease_seconds: int = 300) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self.database = str(database)
        self.lease_seconds = lease_seconds
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_webhook_events (
                    provider_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    processed INTEGER NOT NULL DEFAULT 0,
                    fingerprint TEXT,
                    lease_until TEXT,
                    PRIMARY KEY (provider_id, event_id)
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(payment_webhook_events)")}
            if "fingerprint" not in columns:
                connection.execute("ALTER TABLE payment_webhook_events ADD COLUMN fingerprint TEXT")
            if "lease_until" not in columns:
                connection.execute("ALTER TABLE payment_webhook_events ADD COLUMN lease_until TEXT")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def reserve(self, provider_id: str, event_id: str, fingerprint: str, *, now: datetime) -> bool:
        if now.tzinfo is None or now.utcoffset() != timezone.utc.utcoffset(now):
            raise ValueError("now must be timezone-aware UTC")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT processed, fingerprint, lease_until
                FROM payment_webhook_events
                WHERE provider_id = ? AND event_id = ?
                """,
                (provider_id, event_id),
            ).fetchone()
            lease_until = now + timedelta(seconds=self.lease_seconds)
            if row is not None:
                if row[1] is not None and row[1] != fingerprint:
                    raise ValueError("webhook event payload fingerprint mismatch")
                if row[0]:
                    connection.commit()
                    return False
                existing_lease = datetime.fromisoformat(row[2]) if row[2] else None
                if existing_lease is not None and existing_lease > now:
                    connection.commit()
                    return False
                connection.execute(
                    "UPDATE payment_webhook_events SET fingerprint = ?, lease_until = ? WHERE provider_id = ? AND event_id = ?",
                    (fingerprint, lease_until.isoformat(), provider_id, event_id),
                )
                connection.commit()
                return True
            connection.execute(
                """
                INSERT INTO payment_webhook_events (
                    provider_id, event_id, processed, fingerprint, lease_until
                ) VALUES (?, ?, 0, ?, ?)
                """,
                (provider_id, event_id, fingerprint, lease_until.isoformat()),
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
                SET processed = 1, lease_until = NULL
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
                UPDATE payment_webhook_events
                SET lease_until = NULL
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
