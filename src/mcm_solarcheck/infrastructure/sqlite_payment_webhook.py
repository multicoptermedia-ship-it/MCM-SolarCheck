"""Persistent replay guard for authenticated payment provider events."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4


class WebhookReplayStatus(str, Enum):
    ACQUIRED = "acquired"
    PROCESSING = "processing"
    PROCESSED = "processed"


@dataclass(frozen=True)
class WebhookReplayReservation:
    status: WebhookReplayStatus
    lease_token: str | None = None


class SQLitePaymentWebhookReplayStore:
    def __init__(self, database: str | Path, *, lease_seconds: int = 300) -> None:
        if (
            not isinstance(lease_seconds, int)
            or isinstance(lease_seconds, bool)
            or lease_seconds <= 0
        ):
            raise ValueError("lease_seconds must be a positive integer")
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
                    lease_token TEXT,
                    PRIMARY KEY (provider_id, event_id)
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(payment_webhook_events)"
                )
            }
            if "fingerprint" not in columns:
                connection.execute(
                    "ALTER TABLE payment_webhook_events ADD COLUMN fingerprint TEXT"
                )
            if "lease_until" not in columns:
                connection.execute(
                    "ALTER TABLE payment_webhook_events ADD COLUMN lease_until TEXT"
                )
            if "lease_token" not in columns:
                connection.execute(
                    "ALTER TABLE payment_webhook_events ADD COLUMN lease_token TEXT"
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database, timeout=30)

    def reserve(
        self,
        provider_id: str,
        event_id: str,
        fingerprint: str,
        *,
        now: datetime,
    ) -> WebhookReplayReservation:
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
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
            token = uuid4().hex
            if row is not None:
                if row[1] is not None and row[1] != fingerprint:
                    raise ValueError("webhook event payload fingerprint mismatch")
                if row[0]:
                    connection.commit()
                    return WebhookReplayReservation(WebhookReplayStatus.PROCESSED)
                existing_lease = datetime.fromisoformat(row[2]) if row[2] else None
                if existing_lease is not None and existing_lease > now:
                    connection.commit()
                    return WebhookReplayReservation(WebhookReplayStatus.PROCESSING)
                connection.execute(
                    """
                    UPDATE payment_webhook_events
                    SET fingerprint = ?, lease_until = ?, lease_token = ?
                    WHERE provider_id = ? AND event_id = ?
                    """,
                    (
                        fingerprint,
                        lease_until.isoformat(),
                        token,
                        provider_id,
                        event_id,
                    ),
                )
                connection.commit()
                return WebhookReplayReservation(
                    WebhookReplayStatus.ACQUIRED,
                    token,
                )
            connection.execute(
                """
                INSERT INTO payment_webhook_events (
                    provider_id, event_id, processed, fingerprint,
                    lease_until, lease_token
                ) VALUES (?, ?, 0, ?, ?, ?)
                """,
                (
                    provider_id,
                    event_id,
                    fingerprint,
                    lease_until.isoformat(),
                    token,
                ),
            )
            connection.commit()
            return WebhookReplayReservation(WebhookReplayStatus.ACQUIRED, token)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_processed(
        self, provider_id: str, event_id: str, lease_token: str
    ) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE payment_webhook_events
                SET processed = 1, lease_until = NULL, lease_token = NULL
                WHERE provider_id = ? AND event_id = ?
                  AND processed = 0 AND lease_token = ?
                """,
                (provider_id, event_id, lease_token),
            )
            if cursor.rowcount != 1:
                raise ValueError("webhook replay lease ownership lost")

    def release(
        self, provider_id: str, event_id: str, lease_token: str
    ) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE payment_webhook_events
                SET lease_until = NULL, lease_token = NULL
                WHERE provider_id = ? AND event_id = ?
                  AND processed = 0 AND lease_token = ?
                """,
                (provider_id, event_id, lease_token),
            )
            if cursor.rowcount != 1:
                raise ValueError("webhook replay lease ownership lost")

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
