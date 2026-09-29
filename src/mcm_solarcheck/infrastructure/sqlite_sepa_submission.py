"""SQLite persistence for crash-safe SEPA submission intents."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.sepa_submission import (
    SepaSubmission,
    SepaSubmissionStatus,
)


class SQLiteSepaSubmissionStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
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
                    provider_reference TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def reserve(self, submission: SepaSubmission) -> SepaSubmission:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT mandate_id, user_id, project_id, provider_id,
                       idempotency_key, status, provider_reference
                FROM sepa_submissions
                WHERE payment_id = ?
                """,
                (submission.payment_id,),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO sepa_submissions (
                        payment_id, mandate_id, user_id, project_id,
                        provider_id, idempotency_key, status, provider_reference
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        submission.payment_id,
                        submission.mandate_id,
                        submission.user_id,
                        submission.project_id,
                        submission.provider_id,
                        submission.idempotency_key,
                        submission.status.value,
                        submission.provider_reference,
                    ),
                )
                connection.commit()
                return submission

            existing = SepaSubmission(
                submission.payment_id,
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                SepaSubmissionStatus(row[5]),
                row[6],
            )
            if existing != submission:
                if existing.status is SepaSubmissionStatus.PENDING:
                    expected = SepaSubmission(
                        existing.payment_id,
                        submission.mandate_id,
                        submission.user_id,
                        submission.project_id,
                        submission.provider_id,
                        submission.idempotency_key,
                    )
                    if existing != expected:
                        raise ValueError("conflicting SEPA submission intent")
                else:
                    raise ValueError("SEPA submission already completed")
            connection.commit()
            return existing
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_submitted(
        self, payment_id: str, provider_reference: str
    ) -> SepaSubmission:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT mandate_id, user_id, project_id, provider_id,
                       idempotency_key, status, provider_reference
                FROM sepa_submissions
                WHERE payment_id = ?
                """,
                (payment_id,),
            ).fetchone()
            if row is None:
                raise KeyError(payment_id)
            current = SepaSubmission(
                payment_id,
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                SepaSubmissionStatus(row[5]),
                row[6],
            )
            if current.status is SepaSubmissionStatus.SUBMITTED:
                if current.provider_reference != provider_reference:
                    raise ValueError("SEPA provider reference mismatch")
                connection.commit()
                return current

            updated = current.submitted(provider_reference)
            connection.execute(
                """
                UPDATE sepa_submissions
                SET status = ?, provider_reference = ?
                WHERE payment_id = ?
                """,
                (
                    updated.status.value,
                    updated.provider_reference,
                    payment_id,
                ),
            )
            connection.commit()
            return updated
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, payment_id: str) -> SepaSubmission:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT mandate_id, user_id, project_id, provider_id,
                       idempotency_key, status, provider_reference
                FROM sepa_submissions
                WHERE payment_id = ?
                """,
                (payment_id,),
            ).fetchone()
        if row is None:
            raise KeyError(payment_id)
        return SepaSubmission(
            payment_id,
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            SepaSubmissionStatus(row[5]),
            row[6],
        )
