"""Provider-neutral billing eligibility for delivered compute results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComputeJobDelivery:
    """Evidence that a compute result was successfully delivered to the user."""

    job_id: str
    export_completed: bool = False
    report_retrieved: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.job_id, str) or not self.job_id.strip():
            raise ValueError("job_id must be a non-empty string")

    @property
    def billable(self) -> bool:
        """Become billable only after export completion and report retrieval."""
        return self.export_completed and self.report_retrieved
