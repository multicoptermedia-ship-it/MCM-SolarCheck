"""Provider-neutral worker dispatch contracts."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobLease


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
