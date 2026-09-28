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
