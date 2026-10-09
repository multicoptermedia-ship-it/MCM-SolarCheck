"""Durable upload attempt journal; independent of filesystem commit."""
from __future__ import annotations

import sqlite3
import re
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
            columns = {row[1] for row in connection.execute("PRAGMA table_info(upload_attempts)")}
            if "expected_size" not in columns:
                connection.execute("ALTER TABLE upload_attempts ADD COLUMN expected_size INTEGER")
            if "expected_sha256" not in columns:
                connection.execute("ALTER TABLE upload_attempts ADD COLUMN expected_sha256 TEXT")
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_upload_attempts_pending
                ON upload_attempts (state, created_at)
            """)

    def begin(self, *, customer_id: str, project_id: str, filename: str,
              expected_size: int | None = None, expected_sha256: str | None = None) -> str:
        if any(not isinstance(v, str) or not v.strip() for v in (customer_id, project_id, filename)):
            raise ValueError("upload attempt identity is required")
        if expected_size is not None and (type(expected_size) is not int or expected_size < 0):
            raise ValueError("expected_size must be a nonnegative integer")
        if expected_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError("expected_sha256 must be lowercase SHA-256 hex")
        attempt_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "INSERT INTO upload_attempts (attempt_id, customer_id, project_id, filename, state, created_at, updated_at, expected_size, expected_sha256) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)",
                (attempt_id, customer_id, project_id, filename, now, now, expected_size, expected_sha256),
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

    def pending_with_integrity(self):
        """Read pending records with expected byte count and SHA-256."""
        with sqlite3.connect(self.database) as connection:
            return connection.execute(
                "SELECT attempt_id, customer_id, project_id, filename, expected_size, expected_sha256 FROM upload_attempts WHERE state = 'pending' ORDER BY created_at, attempt_id"
            ).fetchall()

    def finish_verified_if_unique(self, attempt_id: str) -> bool:
        """Atomically finalize only a pending attempt without competing pending names."""
        if not attempt_id:
            raise ValueError("attempt_id is required")
        with sqlite3.connect(self.database) as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """UPDATE upload_attempts SET state = 'completed', updated_at = ?
                   WHERE attempt_id = ? AND state = 'pending'
                   AND expected_size IS NOT NULL AND expected_sha256 IS NOT NULL
                   AND NOT EXISTS (
                       SELECT 1 FROM upload_attempts AS other
                       WHERE other.customer_id = upload_attempts.customer_id
                       AND other.project_id = upload_attempts.project_id
                       AND other.filename = upload_attempts.filename
                       AND other.attempt_id != upload_attempts.attempt_id
                       AND other.state = 'pending'
                   )""",
                (datetime.now(timezone.utc).isoformat(), attempt_id),
            )
            return cursor.rowcount == 1
