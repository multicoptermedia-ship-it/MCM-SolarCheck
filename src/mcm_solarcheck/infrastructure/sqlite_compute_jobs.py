"""SQLite adapter for authoritative online compute job state."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.compute_jobs import (
    ComputeCapacity,
    ComputeJob,
    ComputeJobStatus,
    transition_job,
)


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
                    status TEXT NOT NULL,\n                    worker_id TEXT\n                )
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

    def claim(self, job_id: str, worker_id: str) -> ComputeJob:
        """Atomically assign one running job to exactly one worker."""
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ValueError("worker_id must be a non-empty string")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT job_id, user_id, project_id, status, worker_id
                FROM compute_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                raise KeyError(job_id)
            job = ComputeJob(row[0], row[1], row[2], ComputeJobStatus(row[3]))
            if job.status is not ComputeJobStatus.RUNNING:
                raise ValueError("only a running compute job can be claimed")
            if row[4] not in (None, worker_id):
                raise RuntimeError("compute job already claimed by another worker")
            connection.execute(
                "UPDATE compute_jobs SET worker_id = ? WHERE job_id = ?",
                (worker_id, job_id),
            )
            connection.commit()
            return job
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def release_claim(self, job_id: str, worker_id: str) -> ComputeJob:
        """Atomically release a running job only for its owning worker."""
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ValueError("worker_id must be a non-empty string")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT job_id, user_id, project_id, status, worker_id
                FROM compute_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                raise KeyError(job_id)
            job = ComputeJob(row[0], row[1], row[2], ComputeJobStatus(row[3]))
            if job.status is not ComputeJobStatus.RUNNING:
                raise ValueError("only a running compute job claim can be released")
            if row[4] != worker_id:
                raise PermissionError("compute job worker claim mismatch")
            connection.execute(
                "UPDATE compute_jobs SET worker_id = NULL WHERE job_id = ?",
                (job_id,),
            )
            connection.commit()
            return job
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def finish_claimed(
        self,
        job_id: str,
        worker_id: str,
        *,
        succeeded: bool,
    ) -> ComputeJob:
        """Atomically finish a running job only for its owning worker."""
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ValueError("worker_id must be a non-empty string")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT job_id, user_id, project_id, status, worker_id
                FROM compute_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                raise KeyError(job_id)
            job = ComputeJob(row[0], row[1], row[2], ComputeJobStatus(row[3]))
            if job.status is not ComputeJobStatus.RUNNING:
                raise ValueError("only a running compute job can be finished")
            if row[4] != worker_id:
                raise PermissionError("compute job worker claim mismatch")
            status = ComputeJobStatus.COMPLETED if succeeded else ComputeJobStatus.FAILED
            finished = transition_job(job, status)
            connection.execute(
                "UPDATE compute_jobs SET status = ? WHERE job_id = ?",
                (finished.status.value, finished.job_id),
            )
            connection.commit()
            return finished
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def try_start(self, job: ComputeJob, capacity: ComputeCapacity) -> ComputeJob:
        """Atomically reserve capacity and persist the running transition."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT user_id, project_id, status FROM compute_jobs WHERE job_id = ?",
                (job.job_id,),
            ).fetchone()
            if row is None:
                raise KeyError(job.job_id)
            current = ComputeJob(job.job_id, row[0], row[1], ComputeJobStatus(row[2]))
            if current != job:
                raise ValueError("compute job changed before admission")
            running = connection.execute(
                "SELECT COUNT(*) FROM compute_jobs WHERE status = ?",
                (ComputeJobStatus.RUNNING.value,),
            ).fetchone()[0]
            if not capacity.can_start(int(running)):
                connection.commit()
                return current
            started = transition_job(current, ComputeJobStatus.RUNNING)
            connection.execute(
                "UPDATE compute_jobs SET status = ? WHERE job_id = ?",
                (started.status.value, started.job_id),
            )
            connection.commit()
            return started
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def running_jobs(self) -> int:
        """Return the authoritative number of jobs occupying worker capacity."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM compute_jobs
                WHERE status = ?
                """,
                (ComputeJobStatus.RUNNING.value,),
            ).fetchone()
        return int(row[0])

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
