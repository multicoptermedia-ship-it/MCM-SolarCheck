"""Append-only, customer-scoped audit events for optional training consent."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SQLiteTrainingConsentStore:
    def __init__(self, database: str | Path):
        self.database = str(database)
        with sqlite3.connect(self.database) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS training_consent_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    event TEXT NOT NULL CHECK(event IN ('granted','withdrawn')),
                    notice_version TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                )
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_consent_latest
                ON training_consent_events (customer_id, project_id, id DESC)
            """)

    def record(self, *, customer_id: str, project_id: str, event: str, notice_version: str) -> None:
        if any(not isinstance(v, str) or not v.strip() for v in (customer_id, project_id, notice_version)):
            raise ValueError("consent identity and notice version are required")
        if event not in ("granted", "withdrawn"):
            raise ValueError("invalid consent event")
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "INSERT INTO training_consent_events (customer_id, project_id, event, notice_version, occurred_at) VALUES (?, ?, ?, ?, ?)",
                (customer_id, project_id, event, notice_version, datetime.now(timezone.utc).isoformat()),
            )

    def is_granted(self, *, customer_id: str, project_id: str) -> bool:
        with sqlite3.connect(self.database) as connection:
            row = connection.execute(
                "SELECT event FROM training_consent_events WHERE customer_id = ? AND project_id = ? ORDER BY id DESC LIMIT 1",
                (customer_id, project_id),
            ).fetchone()
        return row is not None and row[0] == "granted"

    def events(self, *, customer_id: str, project_id: str) -> list[tuple[str, str, str]]:
        with sqlite3.connect(self.database) as connection:
            return connection.execute(
                "SELECT event, notice_version, occurred_at FROM training_consent_events WHERE customer_id = ? AND project_id = ? ORDER BY id",
                (customer_id, project_id),
            ).fetchall()
