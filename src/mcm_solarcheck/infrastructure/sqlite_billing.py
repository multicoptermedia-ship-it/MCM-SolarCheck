"""SQLite persistence for compute delivery and billing state."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobDelivery


class SQLiteComputeJobBillingStore:
    """Persist authoritative billing eligibility independently of payment."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS compute_job_billing (
                    job_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    export_completed INTEGER NOT NULL,
                    report_retrieved INTEGER NOT NULL,
                    billing_released INTEGER NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def create(self, billing: ComputeJobBilling) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO compute_job_billing (
                    job_id, user_id, project_id,
                    export_completed, report_retrieved, billing_released
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    billing.delivery.job_id,
                    billing.delivery.user_id,
                    billing.delivery.project_id,
                    billing.delivery.export_completed,
                    billing.delivery.report_retrieved,
                    billing.billing_released,
                ),
            )

    def get(self, job_id: str) -> ComputeJobBilling:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT user_id, project_id,
                       export_completed, report_retrieved, billing_released
                FROM compute_job_billing
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return ComputeJobBilling(
            ComputeJobDelivery(
                job_id,
                row[0],
                row[1],
                export_completed=bool(row[2]),
                report_retrieved=bool(row[3]),
            ),
            billing_released=bool(row[4]),
        )

    def replace(self, billing: ComputeJobBilling) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE compute_job_billing
                SET export_completed = ?, report_retrieved = ?, billing_released = ?
                WHERE job_id = ?
                """,
                (
                    billing.delivery.export_completed,
                    billing.delivery.report_retrieved,
                    billing.billing_released,
                    billing.delivery.job_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(billing.delivery.job_id)
