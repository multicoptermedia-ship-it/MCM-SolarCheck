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

    def mark_export_completed(
        self, job_id: str, user_id: str, project_id: str
    ) -> ComputeJobBilling:
        return self._mark_delivery(job_id, user_id, project_id, "export_completed")

    def mark_report_retrieved(
        self, job_id: str, user_id: str, project_id: str
    ) -> ComputeJobBilling:
        return self._mark_delivery(job_id, user_id, project_id, "report_retrieved")

    def _mark_delivery(
        self, job_id: str, user_id: str, project_id: str, field: str
    ) -> ComputeJobBilling:
        if field not in {"export_completed", "report_retrieved"}:
            raise ValueError("unsupported delivery field")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT user_id, project_id
                FROM compute_job_billing
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                raise KeyError(job_id)
            if row[0] != user_id or row[1] != project_id:
                raise PermissionError("compute job billing ownership mismatch")
            connection.execute(
                f"UPDATE compute_job_billing SET {field} = 1 WHERE job_id = ?",
                (job_id,),
            )
            connection.commit()
            return self.get(job_id)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def release(
        self,
        job_id: str,
        user_id: str,
        project_id: str,
    ) -> ComputeJobBilling:
        """Atomically release a delivered job for billing exactly once."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
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
            if row[0] != user_id or row[1] != project_id:
                raise PermissionError("compute job billing ownership mismatch")

            billing = ComputeJobBilling(
                ComputeJobDelivery(
                    job_id,
                    row[0],
                    row[1],
                    export_completed=bool(row[2]),
                    report_retrieved=bool(row[3]),
                ),
                billing_released=bool(row[4]),
            )
            released = billing.release()
            connection.execute(
                """
                UPDATE compute_job_billing
                SET billing_released = 1
                WHERE job_id = ?
                """,
                (job_id,),
            )
            connection.commit()
            return released
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
