"""SQLite-exclusive SFTP retry leases; no network execution or automatic scheduling."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone


def _utc(now):
    value = datetime.now(timezone.utc) if now is None else now
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return value.astimezone(timezone.utc)


def _identity(*values):
    if any(not isinstance(v, str) or not v or len(v) > 256 for v in values):
        raise ValueError("invalid retry lease identity")


class SQLiteSFTPPreflightRetryLeases:
    """Lease claims require the retry ledger and lease table in the SAME SQLite database."""

    def __init__(self, database):
        self.database = str(database)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sftp_preflight_retry_leases (
                job_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL,
                project_id TEXT NOT NULL, worker_id TEXT NOT NULL,
                token TEXT NOT NULL, expires_at TEXT NOT NULL
            )""")

    def _connect(self):
        return sqlite3.connect(self.database, timeout=10)

    def claim(self, job_id, customer_id, project_id, worker_id, *, now=None, lease_seconds=60):
        _identity(job_id, customer_id, project_id, worker_id)
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 1 and 3600")
        instant = _utc(now)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            retry = db.execute(
                """SELECT customer_id, project_id, attempts, next_attempt_at, state
                FROM sftp_preflight_retries WHERE job_id=?""", (job_id,)
            ).fetchone()
            if retry is None:
                return ("unrecorded", None)
            if retry[:2] != (customer_id, project_id):
                raise PermissionError("retry ownership mismatch")
            if retry[4] != "waiting" or retry[2] >= 3 or not retry[3]:
                return ("manual_review", None)
            deadline = datetime.fromisoformat(retry[3])
            if deadline.tzinfo is None or instant < deadline:
                return ("wait", None)
            existing = db.execute(
                """SELECT customer_id, project_id, expires_at
                FROM sftp_preflight_retry_leases WHERE job_id=?""", (job_id,)
            ).fetchone()
            if existing:
                if existing[:2] != (customer_id, project_id):
                    raise PermissionError("lease ownership mismatch")
                if instant < datetime.fromisoformat(existing[2]):
                    return ("busy", None)
            token = uuid.uuid4().hex
            expiry = (instant + timedelta(seconds=lease_seconds)).isoformat()
            db.execute(
                """INSERT INTO sftp_preflight_retry_leases
                (job_id, customer_id, project_id, worker_id, token, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET worker_id=excluded.worker_id,
                token=excluded.token, expires_at=excluded.expires_at""",
                (job_id, customer_id, project_id, worker_id, token, expiry),
            )
            return ("claimed", token)

    def renew(self, job_id, customer_id, project_id, worker_id, token, *, now=None, lease_seconds=60):
        """Extend only a still-live lease owned by the exact token and identity."""
        _identity(job_id, customer_id, project_id, worker_id, token)
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 1 and 3600")
        instant = _utc(now)
        expiry = (instant + timedelta(seconds=lease_seconds)).isoformat()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT expires_at FROM sftp_preflight_retry_leases
                WHERE job_id=? AND customer_id=? AND project_id=?
                AND worker_id=? AND token=?""",
                (job_id, customer_id, project_id, worker_id, token),
            ).fetchone()
            if row is None:
                return False
            previous = datetime.fromisoformat(row[0])
            if previous.tzinfo is None or instant >= previous:
                return False
            retry = db.execute(
                """SELECT customer_id, project_id, attempts, state
                FROM sftp_preflight_retries WHERE job_id=?""", (job_id,),
            ).fetchone()
            if retry is None or retry[:2] != (customer_id, project_id) or retry[2] >= 3 or retry[3] != "waiting":
                return False
            # Never shorten a lease when clocks or callers disagree.
            if datetime.fromisoformat(expiry) <= previous:
                return True
            return db.execute(
                """UPDATE sftp_preflight_retry_leases SET expires_at=?
                WHERE job_id=? AND customer_id=? AND project_id=?
                AND worker_id=? AND token=? AND expires_at=?""",
                (expiry, job_id, customer_id, project_id, worker_id, token, row[0]),
            ).rowcount == 1

    def owns_live_lease(self, job_id, customer_id, project_id, worker_id, token, *, now=None):
        """Fail closed unless this exact token still owns a live retryable lease."""
        _identity(job_id, customer_id, project_id, worker_id, token)
        instant = _utc(now)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT expires_at FROM sftp_preflight_retry_leases
                WHERE job_id=? AND customer_id=? AND project_id=? AND worker_id=? AND token=?""",
                (job_id, customer_id, project_id, worker_id, token),
            ).fetchone()
            if row is None:
                return False
            expiry = datetime.fromisoformat(row[0])
            if expiry.tzinfo is None or instant >= expiry:
                return False
            retry = db.execute(
                """SELECT customer_id, project_id, attempts, state
                FROM sftp_preflight_retries WHERE job_id=?""", (job_id,),
            ).fetchone()
            return bool(
                retry is not None and retry[:2] == (customer_id, project_id)
                and retry[2] < 3 and retry[3] == "waiting"
            )

    def release(self, job_id, customer_id, project_id, worker_id, token):
        _identity(job_id, customer_id, project_id, worker_id, token)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            return db.execute(
                """DELETE FROM sftp_preflight_retry_leases
                WHERE job_id=? AND customer_id=? AND project_id=? AND worker_id=? AND token=?""",
                (job_id, customer_id, project_id, worker_id, token),
            ).rowcount == 1
