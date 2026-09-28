"""SQLite adapter for authoritative online compute job state."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus


class SQLiteComputeJobStore:
    """Persist compute jobs in a local SQLite database."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS compute_jobs (
                    job_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

    def create(self, job: ComputeJob) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO compute_jobs (job_id, user_id, project_id, status)
                    VALUES (?, ?, ?, ?)
                    """,
                    (job.job_id, job.user_id, job.project_id, job.status.value),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("compute job already exists") from exc

    def get(self, job_id: str) -> ComputeJob:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT job_id, user_id, project_id, status
                FROM compute_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return ComputeJob(
            job_id=row[0],
            user_id=row[1],
            project_id=row[2],
            status=ComputeJobStatus(row[3]),
        )

    def replace(self, job: ComputeJob) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE compute_jobs
                SET user_id = ?, project_id = ?, status = ?
                WHERE job_id = ?
                """,
                (job.user_id, job.project_id, job.status.value, job.job_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(job.job_id)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)
