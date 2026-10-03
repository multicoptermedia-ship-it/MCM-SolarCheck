"""SQLite persistence for crash-safe SEPA submission intents."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from mcm_solarcheck.services.sepa_submission import (
    SepaSubmission,
    SepaSubmissionStatus,
)


class SQLiteSepaSubmissionStore:
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
                CREATE TABLE IF NOT EXISTS sepa_submissions (
                    payment_id TEXT PRIMARY KEY,
                    mandate_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    provider_reference TEXT,
                    lease_token TEXT,
                    lease_until TEXT
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(sepa_submissions)")
            }
            if "lease_token" not in columns:
                connection.execute(
                    "ALTER TABLE sepa_submissions ADD COLUMN lease_token TEXT"
                )
            if "lease_until" not in columns:
                connection.execute(
                    "ALTER TABLE sepa_submissions ADD COLUMN lease_until TEXT"
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database, timeout=30)

    @staticmethod
    def _from_row(payment_id: str, row) -> SepaSubmission:
        return SepaSubmission(
            payment_id,
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            SepaSubmissionStatus(row[5]),
            row[6],
            row[7],
            row[8],
        )

    def reserve(self, submission: SepaSubmission, *, now: datetime) -> SepaSubmission:
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise ValueError("now must be timezone-aware UTC")
        if submission.status is not SepaSubmissionStatus.PENDING:
            raise ValueError("new SEPA submission intent must be pending")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT mandate_id, user_id, project_id, provider_id,
                       idempotency_key, status, provider_reference,
                       lease_token, lease_until
                FROM sepa_submissions
                WHERE payment_id = ?
                """,
                (submission.payment_id,),
            ).fetchone()
            token = uuid4().hex
            lease_until = now + timedelta(seconds=self.lease_seconds)
            if row is None:
                claimed = replace(
                    submission,
                    lease_token=token,
                    lease_until=lease_until.isoformat(),
                )
                connection.execute(
                    """
                    INSERT INTO sepa_submissions (
                        payment_id, mandate_id, user_id, project_id,
                        provider_id, idempotency_key, status, provider_reference,
                        lease_token, lease_until
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        claimed.payment_id,
                        claimed.mandate_id,
                        claimed.user_id,
                        claimed.project_id,
                        claimed.provider_id,
                        claimed.idempotency_key,
                        claimed.status.value,
                        claimed.provider_reference,
                        claimed.lease_token,
                        claimed.lease_until,
                    ),
                )
                connection.commit()
                return claimed

            existing = self._from_row(submission.payment_id, row)
            expected = replace(
                submission,
                lease_token=existing.lease_token,
                lease_until=existing.lease_until,
            )
            if existing.status is SepaSubmissionStatus.SUBMITTED:
                connection.commit()
                return existing
            if existing != expected:
                raise ValueError("conflicting SEPA submission intent")
            existing_until = (
                datetime.fromisoformat(existing.lease_until)
                if existing.lease_until
                else None
            )
            if existing_until is not None and existing_until > now:
                raise RuntimeError("SEPA submission is already being processed")
            claimed = replace(
                existing,
                lease_token=token,
                lease_until=lease_until.isoformat(),
            )
            connection.execute(
                """
                UPDATE sepa_submissions
                SET lease_token = ?, lease_until = ?
                WHERE payment_id = ?
                """,
                (claimed.lease_token, claimed.lease_until, submission.payment_id),
            )
            connection.commit()
            return claimed
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_submitted(
        self, payment_id: str, provider_reference: str, lease_token: str
    ) -> SepaSubmission:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT mandate_id, user_id, project_id, provider_id,
                       idempotency_key, status, provider_reference,
                       lease_token, lease_until
                FROM sepa_submissions
                WHERE payment_id = ?
                """,
                (payment_id,),
            ).fetchone()
            if row is None:
                raise KeyError(payment_id)
            current = self._from_row(payment_id, row)
            if current.status is SepaSubmissionStatus.SUBMITTED:
                if current.provider_reference != provider_reference:
                    raise ValueError("SEPA provider reference mismatch")
                connection.commit()
                return current
            if current.lease_token != lease_token:
                raise ValueError("SEPA submission lease ownership lost")

            updated = current.submitted(provider_reference)
            connection.execute(
                """
                UPDATE sepa_submissions
                SET status = ?, provider_reference = ?,
                    lease_token = NULL, lease_until = NULL
                WHERE payment_id = ? AND lease_token = ?
                """,
                (
                    updated.status.value,
                    updated.provider_reference,
                    payment_id,
                    lease_token,
                ),
            )
            connection.commit()
            return updated
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def release(self, payment_id: str, lease_token: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE sepa_submissions
                SET lease_token = NULL, lease_until = NULL
                WHERE payment_id = ? AND status = ? AND lease_token = ?
                """,
                (payment_id, SepaSubmissionStatus.PENDING.value, lease_token),
            )
            if cursor.rowcount != 1:
                raise ValueError("SEPA submission lease ownership lost")

    def get(self, payment_id: str) -> SepaSubmission:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT mandate_id, user_id, project_id, provider_id,
                       idempotency_key, status, provider_reference,
                       lease_token, lease_until
                FROM sepa_submissions
                WHERE payment_id = ?
                """,
                (payment_id,),
            ).fetchone()
        if row is None:
            raise KeyError(payment_id)
        return self._from_row(payment_id, row)
