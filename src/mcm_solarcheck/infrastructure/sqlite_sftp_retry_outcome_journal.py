"""Atomic, lease-fenced SQLite journal of sanitized SFTP retry preflight outcomes."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from mcm_solarcheck.services.sftp_retry_inspection_summary import RetryInspectionSummary

_ALLOWED = frozenset(("ready", "missing_directory"))


class SQLiteSFTPRetryOutcomeJournal:
    def __init__(self, database):
        self.database = str(database)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sftp_retry_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL, customer_id TEXT NOT NULL,
                project_id TEXT NOT NULL, worker_id TEXT NOT NULL,
                token TEXT NOT NULL, status TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                UNIQUE(job_id, token)
            )""")

    def _connect(self):
        return sqlite3.connect(self.database, timeout=10)

    def record(self, identity, summary: RetryInspectionSummary, *, now=None):
        from mcm_solarcheck.services.sftp_preflight_retry_work_guard import RetryWorkIdentity
        if not isinstance(identity, RetryWorkIdentity) or not isinstance(summary, RetryInspectionSummary):
            raise TypeError("typed identity and summary required")
        values = (identity.job_id, identity.customer_id, identity.project_id, identity.worker_id, identity.token)
        if any(not isinstance(v, str) or not v or len(v) > 256 for v in values):
            raise ValueError("invalid retry identity")
        if (summary.job_id, summary.customer_id, summary.project_id) != values[:3]:
            raise PermissionError("outcome identity mismatch")
        if summary.status not in _ALLOWED:
            raise ValueError("only completed read-only inspections may be recorded")
        instant = datetime.now(timezone.utc) if now is None else now
        if not isinstance(instant, datetime) or instant.tzinfo is None:
            raise ValueError("timezone-aware timestamp required")
        instant = instant.astimezone(timezone.utc)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT expires_at FROM sftp_preflight_retry_leases
                WHERE job_id=? AND customer_id=? AND project_id=?
                AND worker_id=? AND token=?""", values
            ).fetchone()
            retry = db.execute(
                """SELECT customer_id, project_id, attempts, state
                FROM sftp_preflight_retries WHERE job_id=?""", (identity.job_id,)
            ).fetchone()
            if (row is None or retry is None or retry[:2] != values[1:3]
                    or retry[2] >= 3 or retry[3] != "waiting"):
                return "lease_lost"
            expiry = datetime.fromisoformat(row[0])
            if expiry.tzinfo is None or instant >= expiry:
                return "lease_lost"
            existing = db.execute(
                "SELECT status FROM sftp_retry_outcomes WHERE job_id=? AND token=?",
                (identity.job_id, identity.token)
            ).fetchone()
            if existing is not None:
                return "already_recorded" if existing[0] == summary.status else "conflict"
            db.execute(
                """INSERT INTO sftp_retry_outcomes
                (job_id,customer_id,project_id,worker_id,token,status,recorded_at)
                VALUES (?,?,?,?,?,?,?)""",
                (*values, summary.status, instant.isoformat())
            )
            return "recorded"

    def history(self, job_id, customer_id, project_id):
        if any(not isinstance(v, str) or not v or len(v) > 256 for v in (job_id, customer_id, project_id)):
            raise ValueError("invalid owner identity")
        with self._connect() as db:
            rows = db.execute(
                """SELECT worker_id,status,recorded_at FROM sftp_retry_outcomes
                WHERE job_id=? AND customer_id=? AND project_id=? ORDER BY id""",
                (job_id, customer_id, project_id)
            ).fetchall()
            return [dict(worker_id=w, status=s, recorded_at=t) for w, s, t in rows]
