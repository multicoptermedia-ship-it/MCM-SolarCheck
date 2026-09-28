"""Provider-neutral online compute job contracts.

The web/product layer submits isolated jobs through this boundary. Concrete
queue and worker providers remain deployment concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ComputeJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ComputeJob:
    job_id: str
    user_id: str
    project_id: str
    status: ComputeJobStatus

    def __post_init__(self) -> None:
        for name, value in (
            ("job_id", self.job_id),
            ("user_id", self.user_id),
            ("project_id", self.project_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.status, ComputeJobStatus):
            raise ValueError("status must be a ComputeJobStatus")


class ComputeJobQueue(Protocol):
    """Queue adapter used by online application services."""

    def submit(self, *, user_id: str, project_id: str) -> ComputeJob:
        """Persist and enqueue one isolated evaluation job."""
        ...

    def get(self, job_id: str) -> ComputeJob:
        """Return the authoritative persisted state for one job."""
        ...


@dataclass(frozen=True)
class ComputeCapacity:
    """Deployment-owned limit for simultaneous evaluation workers."""

    max_parallel_jobs: int

    def __post_init__(self) -> None:
        if type(self.max_parallel_jobs) is not int or self.max_parallel_jobs <= 0:
            raise ValueError("max_parallel_jobs must be a positive integer")

    def can_start(self, running_jobs: int) -> bool:
        if type(running_jobs) is not int or running_jobs < 0:
            raise ValueError("running_jobs must be a non-negative integer")
        return running_jobs < self.max_parallel_jobs

    def admission_status(self, running_jobs: int) -> ComputeJobStatus:
        """Keep excess work queued instead of starting unbounded processes."""
        return (
            ComputeJobStatus.RUNNING
            if self.can_start(running_jobs)
            else ComputeJobStatus.QUEUED
        )


_ALLOWED_STATUS_TRANSITIONS: dict[ComputeJobStatus, frozenset[ComputeJobStatus]] = {
    ComputeJobStatus.QUEUED: frozenset(
        {ComputeJobStatus.RUNNING, ComputeJobStatus.FAILED}
    ),
    ComputeJobStatus.RUNNING: frozenset(
        {ComputeJobStatus.COMPLETED, ComputeJobStatus.FAILED}
    ),
    ComputeJobStatus.COMPLETED: frozenset(),
    ComputeJobStatus.FAILED: frozenset(),
}


def transition_job(job: ComputeJob, status: ComputeJobStatus) -> ComputeJob:
    """Return the next authoritative job state or reject an invalid transition."""
    if not isinstance(status, ComputeJobStatus):
        raise ValueError("status must be a ComputeJobStatus")
    if status not in _ALLOWED_STATUS_TRANSITIONS[job.status]:
        raise ValueError(f"invalid compute job transition: {job.status.value} -> {status.value}")
    return ComputeJob(
        job_id=job.job_id,
        user_id=job.user_id,
        project_id=job.project_id,
        status=status,
    )


class ComputeJobLoad(Protocol):
    """Provider-neutral source for current worker occupancy."""

    def running_jobs(self) -> int:
        """Return the authoritative number of currently running jobs."""
        ...


class ComputeJobStore(Protocol):
    """Persistence boundary for authoritative compute job state."""

    def create(self, job: ComputeJob) -> None:
        """Persist a new job exactly once."""
        ...

    def get(self, job_id: str) -> ComputeJob:
        """Load one authoritative job state."""
        ...

    def replace(self, job: ComputeJob) -> None:
        """Persist the supplied authoritative job state."""
        ...


@dataclass
class ComputeJobService:
    """Server-side boundary that owns persistence and state transitions."""

    store: ComputeJobStore
    load: ComputeJobLoad | None = None

    def create(self, *, job_id: str, user_id: str, project_id: str) -> ComputeJob:
        job = ComputeJob(
            job_id=job_id,
            user_id=user_id,
            project_id=project_id,
            status=ComputeJobStatus.QUEUED,
        )
        self.store.create(job)
        return job

    def get(self, job_id: str, *, user_id: str, project_id: str) -> ComputeJob:
        job = self.store.get(job_id)
        self._require_owner(job, user_id=user_id, project_id=project_id)
        return job

    def start(
        self,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
        capacity: ComputeCapacity,
        running_jobs: int | None = None,
    ) -> ComputeJob:
        current = self.get(job_id, user_id=user_id, project_id=project_id)
        if running_jobs is None:
            if self.load is None:
                raise RuntimeError("compute job load source is required")
            running_jobs = self.load.running_jobs()
        if capacity.admission_status(running_jobs) is ComputeJobStatus.QUEUED:
            return current
        return self.transition(
            job_id,
            ComputeJobStatus.RUNNING,
            user_id=user_id,
            project_id=project_id,
        )

    def transition(
        self,
        job_id: str,
        status: ComputeJobStatus,
        *,
        user_id: str,
        project_id: str,
    ) -> ComputeJob:
        current = self.store.get(job_id)
        self._require_owner(current, user_id=user_id, project_id=project_id)
        transitioned = transition_job(current, status)
        self.store.replace(transitioned)
        return transitioned

    @staticmethod
    def _require_owner(job: ComputeJob, *, user_id: str, project_id: str) -> None:
        if job.user_id != user_id or job.project_id != project_id:
            raise PermissionError("compute job access denied")
