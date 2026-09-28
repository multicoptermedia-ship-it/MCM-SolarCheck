"""Provider-neutral worker dispatch contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from mcm_solarcheck.services.compute_jobs import (
    ComputeJob,
    ComputeJobClaim,
    ComputeJobLease,
)


class ComputeJobDispatch(Protocol):
    """Source of running jobs that are ready for worker claiming."""

    def next_ready(self) -> ComputeJob | None:
        """Return one ready job, or None when no work is available."""
        ...

    def claim_next(
        self,
        worker_id: str,
        lease: ComputeJobLease | None = None,
    ) -> ComputeJob | None:
        """Claim one ready job, including a claim expired at lease.now."""
        ...


@dataclass
class ComputeWorkerService:
    """Provider-neutral worker lifecycle over dispatch and claim boundaries."""

    dispatch: ComputeJobDispatch
    claims: ComputeJobClaim

    def claim_next(
        self,
        *,
        worker_id: str,
        lease: ComputeJobLease | None = None,
    ) -> ComputeJob | None:
        """Claim the next available running job for this worker."""
        return self.dispatch.claim_next(worker_id, lease)

    def renew(
        self,
        job_id: str,
        *,
        worker_id: str,
        lease: ComputeJobLease,
    ) -> ComputeJob:
        """Renew an active lease owned by this worker."""
        return self.claims.renew_claim(job_id, worker_id, lease)

    def release(
        self,
        job_id: str,
        *,
        worker_id: str,
        now: datetime | None = None,
    ) -> ComputeJob:
        """Release a job through its authoritative worker claim."""
        return self.claims.release_claim(job_id, worker_id, now=now)

    def finish(
        self,
        job_id: str,
        *,
        worker_id: str,
        succeeded: bool,
        now: datetime | None = None,
    ) -> ComputeJob:
        """Finish a job through its authoritative worker claim."""
        return self.claims.finish_claimed(
            job_id,
            worker_id,
            succeeded=succeeded,
            now=now,
        )
