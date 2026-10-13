"""Explicit bounded queue dispatcher using authoritative admission and worker ownership.

The caller supplies durable pending job identities; this is not a polling daemon.
"""
from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import Future

from mcm_solarcheck.services.compute_jobs import ComputeCapacity, ComputeJobStatus


@dataclass(frozen=True)
class PendingProjectJob:
    customer_id: str
    project_id: str
    job_id: str

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip() for value in (self.customer_id, self.project_id, self.job_id)):
            raise ValueError("job identity must be nonempty")


class QueuedJobDispatcher:
    """Admit and schedule pending jobs without bypassing ownership checks."""

    def __init__(self, jobs, workers, *, max_parallel_jobs: int = 2):
        self._jobs = jobs
        self._workers = workers
        self._capacity = ComputeCapacity(max_parallel_jobs)

    def dispatch(self, pending: list[PendingProjectJob]) -> dict[str, Future]:
        scheduled: dict[str, Future] = {}
        seen: set[str] = set()
        for item in pending:
            if item.job_id in seen:
                continue
            seen.add(item.job_id)
            job = self._jobs.get(item.job_id, user_id=item.customer_id, project_id=item.project_id)
            if job.status is not ComputeJobStatus.QUEUED:
                continue
            admitted = self._jobs.start(
                item.job_id,
                user_id=item.customer_id,
                project_id=item.project_id,
                capacity=self._capacity,
            )
            if admitted.status is not ComputeJobStatus.RUNNING:
                continue
            scheduled[item.job_id] = self._workers.submit(
                customer_id=item.customer_id,
                project_id=item.project_id,
                job_id=item.job_id,
            )
        return scheduled
