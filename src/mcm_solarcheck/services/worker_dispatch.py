"""Provider-neutral worker dispatch contracts."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.services.compute_jobs import ComputeJob


class ComputeJobDispatch(Protocol):
    """Source of running jobs that are ready for worker claiming."""

    def next_ready(self) -> ComputeJob | None:
        """Return one ready job, or None when no work is available."""
        ...
