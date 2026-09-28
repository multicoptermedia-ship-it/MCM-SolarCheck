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


@dataclass(frozen=True)
class ComputeJobBilling:
    """Persistent billing state separated from payment execution."""

    delivery: ComputeJobDelivery
    billing_released: bool = False

    def release(self) -> "ComputeJobBilling":
        """Release delivered work for billing exactly once."""
        if not self.delivery.billable:
            raise ValueError("compute job delivery is not billable")
        if self.billing_released:
            raise ValueError("compute job billing already released")
        return ComputeJobBilling(self.delivery, billing_released=True)
