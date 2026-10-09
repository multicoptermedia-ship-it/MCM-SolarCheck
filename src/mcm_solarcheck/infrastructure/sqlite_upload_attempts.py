"""Durable upload attempt journal; independent of filesystem commit."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class SQLiteUploadAttemptStore:
    def __init__(self, database: str | Path):
        self.database = str(database)
        with sqlite3.connect(self.database) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS upload_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('pending','completed','failed')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_upload_attempts_pending
                ON upload_attempts (state, created_at)
            """)

    def begin(self, *, customer_id: str, project_id: str, filename: str) -> str:
        if any(not isinstance(v, str) or not v.strip() for v in (customer_id, project_id, filename)):
            raise ValueError("upload attempt identity is required")
        attempt_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "INSERT INTO upload_attempts VALUES (?, ?, ?, ?, 'pending', ?, ?)",
                (attempt_id, customer_id, project_id, filename, now, now),
            )
        return attempt_id

    def finish(self, attempt_id: str, *, succeeded: bool) -> None:
        if not attempt_id:
            raise ValueError("attempt_id is required")
        with sqlite3.connect(self.database) as connection:
            cursor = connection.execute(
                "UPDATE upload_attempts SET state = ?, updated_at = ? WHERE attempt_id = ? AND state = 'pending'",
                ("completed" if succeeded else "failed", datetime.now(timezone.utc).isoformat(), attempt_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("upload attempt is missing or already finalized")

    def pending(self) -> list[tuple[str, str, str, str]]:
        with sqlite3.connect(self.database) as connection:
            return connection.execute(
                "SELECT attempt_id, customer_id, project_id, filename FROM upload_attempts WHERE state = 'pending' ORDER BY created_at, attempt_id"
            ).fetchall()
