"""Provider-neutral billing eligibility for delivered compute results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ComputeJobDelivery:
    """Evidence that a compute result was successfully delivered to the user."""

    job_id: str
    user_id: str
    project_id: str
    export_completed: bool = False
    report_retrieved: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("job_id", self.job_id),
            ("user_id", self.user_id),
            ("project_id", self.project_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

    @property
    def billable(self) -> bool:
        """Become billable only after export completion and report retrieval."""
        return self.export_completed and self.report_retrieved


@dataclass(frozen=True)
class ComputeJobBilling:
    """Persistent billing state separated from payment execution."""

    delivery: ComputeJobDelivery
    billing_released: bool = False

    def __post_init__(self) -> None:
        if self.billing_released and not self.delivery.billable:
            raise ValueError(
                "billing cannot be released before export and report retrieval"
            )

    def release(self) -> "ComputeJobBilling":
        """Release delivered work for billing exactly once."""
        if not self.delivery.billable:
            raise ValueError("compute job delivery is not billable")
        if self.billing_released:
            raise ValueError("compute job billing already released")
        return ComputeJobBilling(self.delivery, billing_released=True)


class ComputeJobBillingStore(Protocol):
    """Persistence boundary for authoritative delivery and billing state."""

    def create(self, billing: ComputeJobBilling) -> None:
        """Persist billing state for one job exactly once."""
        ...

    def get(self, job_id: str) -> ComputeJobBilling:
        """Load authoritative billing state for one job."""
        ...

    def mark_export_completed(
        self, job_id: str, user_id: str, project_id: str
    ) -> ComputeJobBilling:
        """Atomically persist export delivery evidence."""
        ...

    def mark_report_retrieved(
        self, job_id: str, user_id: str, project_id: str
    ) -> ComputeJobBilling:
        """Atomically persist report retrieval evidence."""
        ...

    def release(
        self,
        job_id: str,
        user_id: str,
        project_id: str,
    ) -> ComputeJobBilling:
        """Atomically release one delivered job for billing."""
        ...


@dataclass
class ComputeJobBillingService:
    """Server-owned delivery evidence and billing eligibility transitions."""

    store: ComputeJobBillingStore

    def create(
        self,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
    ) -> ComputeJobBilling:
        billing = ComputeJobBilling(ComputeJobDelivery(job_id, user_id, project_id))
        self.store.create(billing)
        return billing

    def _owned(self, job_id: str, user_id: str, project_id: str) -> ComputeJobBilling:
        current = self.store.get(job_id)
        if (
            current.delivery.user_id != user_id
            or current.delivery.project_id != project_id
        ):
            raise PermissionError("compute job billing ownership mismatch")
        return current

    def mark_export_completed(
        self,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
    ) -> ComputeJobBilling:
        return self.store.mark_export_completed(job_id, user_id, project_id)

    def mark_report_retrieved(
        self,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
    ) -> ComputeJobBilling:
        return self.store.mark_report_retrieved(job_id, user_id, project_id)

    def release(
        self,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
    ) -> ComputeJobBilling:
        return self.store.release(job_id, user_id, project_id)
