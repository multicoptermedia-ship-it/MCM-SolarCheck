"""SQLite evidence for idempotent terminal report recovery notifications."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class SQLiteReportRecoveryStore:
    def __init__(self, database: str | Path, *, lease_seconds: float = 300.0) -> None:
        if lease_seconds <= 0:
            raise ValueError("recovery notification lease must be positive")
        self.database = str(database)
        self.lease_seconds = lease_seconds
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS report_recovery_notification (
                    job_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'sent',
                    lease_until REAL,
                    PRIMARY KEY (job_id, phase)
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(report_recovery_notification)"
                )
            }
            if "status" not in columns:
                connection.execute(
                    "ALTER TABLE report_recovery_notification "
                    "ADD COLUMN status TEXT NOT NULL DEFAULT 'sent'"
                )
            if "lease_until" not in columns:
                connection.execute(
                    "ALTER TABLE report_recovery_notification ADD COLUMN lease_until REAL"
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def claim(self, job_id: str, phase: str) -> bool:
        """Acquire a temporary send lease unless the notification is already sent."""
        now = time.time()
        lease_until = now + self.lease_seconds
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT status, lease_until
                FROM report_recovery_notification
                WHERE job_id = ? AND phase = ?
                """,
                (job_id, phase),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO report_recovery_notification
                        (job_id, phase, status, lease_until)
                    VALUES (?, ?, 'pending', ?)
                    """,
                    (job_id, phase, lease_until),
                )
                return True

            status, current_lease = row
            if status == "sent":
                return False
            if status != "pending":
                raise ValueError("invalid report recovery notification status")
            if current_lease is not None and current_lease > now:
                return False

            connection.execute(
                """
                UPDATE report_recovery_notification
                SET lease_until = ?
                WHERE job_id = ? AND phase = ?
                """,
                (lease_until, job_id, phase),
            )
            return True

    def mark_sent(self, job_id: str, phase: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE report_recovery_notification
                SET status = 'sent', lease_until = NULL
                WHERE job_id = ? AND phase = ? AND status = 'pending'
                """,
                (job_id, phase),
            )
            if cursor.rowcount != 1:
                raise ValueError("report recovery notification is not pending")

    def release(self, job_id: str, phase: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM report_recovery_notification
                WHERE job_id = ? AND phase = ? AND status = 'pending'
                """,
                (job_id, phase),
            )
