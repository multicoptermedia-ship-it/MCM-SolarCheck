"""SQLite persistence for provider-neutral online payments."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.payment import (
    OnlinePayment,
    PaymentAmount,
    PaymentStatus,
)
from mcm_solarcheck.services.payment_methods import PaymentMethod


class SQLiteOnlinePaymentStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS online_payments (
                    payment_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    amount_minor_units INTEGER,
                    currency TEXT,
                    status TEXT NOT NULL,
                    provider_reference TEXT,
                    method TEXT,
                    merchant_account_id TEXT,
                    merchant_account_version INTEGER,
                    provider_id TEXT
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(online_payments)")
            }
            if "method" not in columns:
                connection.execute(
                    "ALTER TABLE online_payments ADD COLUMN method TEXT"
                )
            if "merchant_account_id" not in columns:
                connection.execute(
                    "ALTER TABLE online_payments ADD COLUMN merchant_account_id TEXT"
                )
            if "merchant_account_version" not in columns:
                connection.execute(
                    "ALTER TABLE online_payments ADD COLUMN merchant_account_version INTEGER"
                )
            if "provider_id" not in columns:
                connection.execute(
                    "ALTER TABLE online_payments ADD COLUMN provider_id TEXT"
                )
            duplicate = connection.execute(
                """
                SELECT job_id, COUNT(*)
                FROM online_payments
                GROUP BY job_id
                HAVING COUNT(*) > 1
                LIMIT 1
                """
            ).fetchone()
            if duplicate is not None:
                raise ValueError(
                    "cannot enforce one payment per job: duplicate job payments exist"
                )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    ux_online_payments_job_id
                ON online_payments(job_id)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def create(self, payment: OnlinePayment) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO online_payments (
                    payment_id, user_id, project_id, job_id,
                    amount_minor_units, currency, status, provider_reference, method,
                    merchant_account_id, merchant_account_version, provider_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payment.payment_id,
                    payment.user_id,
                    payment.project_id,
                    payment.job_id,
                    payment.amount.minor_units if payment.amount else None,
                    payment.amount.currency if payment.amount else None,
                    payment.status.value,
                    payment.provider_reference,
                    payment.method.value if payment.method else None,
                    payment.merchant_account_id,
                    payment.merchant_account_version,
                    payment.provider_id,
                ),
            )

    def get(self, payment_id: str) -> OnlinePayment:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT user_id, project_id, job_id, amount_minor_units,
                       currency, status, provider_reference, method,
                       merchant_account_id, merchant_account_version, provider_id
                FROM online_payments
                WHERE payment_id = ?
                """,
                (payment_id,),
            ).fetchone()
        if row is None:
            raise KeyError(payment_id)
        return OnlinePayment(
            payment_id,
            row[0],
            row[1],
            row[2],
            PaymentAmount(row[3], row[4]) if row[3] is not None else None,
            PaymentStatus(row[5]),
            row[6],
            PaymentMethod(row[7]) if row[7] is not None else None,
            row[8],
            row[9],
            row[10],
        )

    def authorize(
        self,
        payment_id: str,
        user_id: str,
        project_id: str,
        provider_reference: str,
    ) -> OnlinePayment:
        return self._transition(
            payment_id,
            user_id,
            project_id,
            lambda payment: payment.authorize(provider_reference),
        )

    def capture(
        self, payment_id: str, user_id: str, project_id: str
    ) -> OnlinePayment:
        return self._transition(
            payment_id, user_id, project_id, lambda payment: payment.capture()
        )

    def void(
        self, payment_id: str, user_id: str, project_id: str
    ) -> OnlinePayment:
        return self._transition(
            payment_id, user_id, project_id, lambda payment: payment.void()
        )

    def _transition(self, payment_id, user_id, project_id, transition):
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT user_id, project_id, job_id, amount_minor_units,
                       currency, status, provider_reference, method,
                       merchant_account_id, merchant_account_version, provider_id
                FROM online_payments
                WHERE payment_id = ?
                """,
                (payment_id,),
            ).fetchone()
            if row is None:
                raise KeyError(payment_id)
            if row[0] != user_id or row[1] != project_id:
                raise PermissionError("payment ownership mismatch")
            current = OnlinePayment(
                payment_id,
                row[0],
                row[1],
                row[2],
                PaymentAmount(row[3], row[4]) if row[3] is not None else None,
                PaymentStatus(row[5]),
                row[6],
                PaymentMethod(row[7]) if row[7] is not None else None,
                row[8],
                row[9],
                row[10],
            )
            updated = transition(current)
            connection.execute(
                """
                UPDATE online_payments
                SET status = ?, provider_reference = ?
                WHERE payment_id = ?
                """,
                (updated.status.value, updated.provider_reference, payment_id),
            )
            connection.commit()
            return updated
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
