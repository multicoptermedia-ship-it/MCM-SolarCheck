"""SQLite evidence for idempotent terminal report recovery notifications."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteReportRecoveryStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS report_recovery_notification (
                    job_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    PRIMARY KEY (job_id, phase)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def claim(self, job_id: str, phase: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO report_recovery_notification (job_id, phase)
                VALUES (?, ?)
                """,
                (job_id, phase),
            )
            return cursor.rowcount == 1

    def release(self, job_id: str, phase: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM report_recovery_notification
                WHERE job_id = ? AND phase = ?
                """,
                (job_id, phase),
            )
