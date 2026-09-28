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

    def replace(self, billing: ComputeJobBilling) -> None:
        """Persist updated authoritative billing state."""
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

    def mark_export_completed(self, job_id: str) -> ComputeJobBilling:
        current = self.store.get(job_id)
        if current.delivery.export_completed:
            return current
        updated = ComputeJobBilling(
            ComputeJobDelivery(
                job_id,
                current.delivery.user_id,
                current.delivery.project_id,
                export_completed=True,
                report_retrieved=current.delivery.report_retrieved,
            ),
            billing_released=current.billing_released,
        )
        self.store.replace(updated)
        return updated

    def mark_report_retrieved(self, job_id: str) -> ComputeJobBilling:
        current = self.store.get(job_id)
        if current.delivery.report_retrieved:
            return current
        updated = ComputeJobBilling(
            ComputeJobDelivery(
                job_id,
                current.delivery.user_id,
                current.delivery.project_id,
                export_completed=current.delivery.export_completed,
                report_retrieved=True,
            ),
            billing_released=current.billing_released,
        )
        self.store.replace(updated)
        return updated

    def release(self, job_id: str) -> ComputeJobBilling:
        current = self.store.get(job_id)
        released = current.release()
        self.store.replace(released)
        return released
