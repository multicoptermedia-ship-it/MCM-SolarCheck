"""Persistent, owner-scoped SFTP preflight retry ledger (no network actions)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

_ALLOWED = {"network", "timeout"}


class SQLiteSFTPPreflightRetries:
    def __init__(self, database):
        self.database = str(database)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sftp_preflight_retries (
                job_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL,
                project_id TEXT NOT NULL, attempts INTEGER NOT NULL,
                next_attempt_at TEXT, state TEXT NOT NULL,
                last_category TEXT NOT NULL
            )""")

    def _connect(self):
        return sqlite3.connect(self.database, timeout=10)

    def record_failure(self, job_id, customer_id, project_id, category, *, now=None):
        if any(not isinstance(x, str) or not x or len(x) > 256 for x in (job_id, customer_id, project_id)):
            raise ValueError("invalid retry identity")
        if not isinstance(category, str) or category not in _ALLOWED:
            raise ValueError("only transient failures can be recorded")
        instant = now if now is not None else datetime.now(timezone.utc)
        if not isinstance(instant, datetime) or instant.tzinfo is None:
            raise ValueError("timezone-aware now required")
        instant = instant.astimezone(timezone.utc)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT customer_id, project_id, attempts, state FROM sftp_preflight_retries WHERE job_id=?",
                (job_id,),
            ).fetchone()
            if row and row[:2] != (customer_id, project_id):
                raise PermissionError("retry job ownership mismatch")
            if row and row[3] == "exhausted":
                return ("exhausted", row[2], None)
            attempts = (row[2] if row else 0) + 1
            exhausted = attempts >= 3
            next_at = None if exhausted else (instant + timedelta(seconds=30 * (2 ** (attempts - 1)))).isoformat()
            state = "exhausted" if exhausted else "waiting"
            db.execute(
                """INSERT INTO sftp_preflight_retries
                (job_id, customer_id, project_id, attempts, next_attempt_at, state, last_category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET attempts=excluded.attempts,
                next_attempt_at=excluded.next_attempt_at, state=excluded.state,
                last_category=excluded.last_category""",
                (job_id, customer_id, project_id, attempts, next_at, state, category),
            )
            return (state, attempts, next_at)

    def inspect(self, job_id, customer_id, project_id):
        with self._connect() as db:
            row = db.execute(
                """SELECT customer_id, project_id, attempts, next_attempt_at, state, last_category
                FROM sftp_preflight_retries WHERE job_id=?""", (job_id,)
            ).fetchone()
        if row is None:
            return None
        if row[:2] != (customer_id, project_id):
            raise PermissionError("retry job ownership mismatch")
        return dict(attempts=row[2], next_attempt_at=row[3], state=row[4], last_category=row[5])
