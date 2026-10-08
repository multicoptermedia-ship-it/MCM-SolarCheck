"""Persistence boundary for authoritative online compute job state."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.services.compute_jobs import ComputeJob


class ComputeJobStore(Protocol):
    """Durable store used by queue/worker adapters.

    Concrete deployments must make state changes atomic where concurrency can
    cause competing workers to claim the same queued job.
    """

    def create(self, job: ComputeJob) -> None:
        """Persist a newly submitted job before it is dispatched."""
        ...

    def get(self, job_id: str) -> ComputeJob:
        """Return the authoritative persisted job state."""
        ...

    def update(self, job: ComputeJob) -> None:
        """Persist an authoritative state change for an existing job."""
        ...
