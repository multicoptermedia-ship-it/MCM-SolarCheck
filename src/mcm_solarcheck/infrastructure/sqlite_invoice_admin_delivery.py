"""SQLite delivery evidence for administrative invoice email."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class SQLiteInvoiceAdminDeliveryStore:
    """Persist a crash-recoverable send lease without storing invoice contents."""

    def __init__(self, database: str | Path, *, lease_seconds: float = 300.0) -> None:
        if lease_seconds <= 0:
            raise ValueError("invoice admin delivery lease must be positive")
        self.database = str(database)
        self.lease_seconds = lease_seconds
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS invoice_admin_delivery (
                    invoice_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    lease_until REAL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def claim(self, invoice_id: str) -> bool:
        now = time.time()
        lease_until = now + self.lease_seconds
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT status, lease_until
                FROM invoice_admin_delivery
                WHERE invoice_id = ?
                """,
                (invoice_id,),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO invoice_admin_delivery
                        (invoice_id, status, lease_until)
                    VALUES (?, 'pending', ?)
                    """,
                    (invoice_id, lease_until),
                )
                return True

            status, current_lease = row
            if status == "sent":
                return False
            if status != "pending":
                raise ValueError("invalid invoice admin delivery status")
            if current_lease is not None and current_lease > now:
                return False
            connection.execute(
                """
                UPDATE invoice_admin_delivery
                SET lease_until = ?
                WHERE invoice_id = ?
                """,
                (lease_until, invoice_id),
            )
            return True

    def mark_sent(self, invoice_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE invoice_admin_delivery
                SET status = 'sent', lease_until = NULL
                WHERE invoice_id = ? AND status = 'pending'
                """,
                (invoice_id,),
            )
            if cursor.rowcount != 1:
                raise ValueError("invoice admin delivery is not pending")

    def release(self, invoice_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM invoice_admin_delivery
                WHERE invoice_id = ? AND status = 'pending'
                """,
                (invoice_id,),
            )
