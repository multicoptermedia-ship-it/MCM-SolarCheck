"""Server-owned access gate for online SolarCheck report delivery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from mcm_solarcheck.services.billing import ComputeJobBilling, ComputeJobBillingStore
from mcm_solarcheck.services.compute_jobs import ComputeJobStatus


@dataclass(frozen=True)
class ReportArtifact:
    job_id: str
    content: bytes
    media_type: str
    filename: str


class ReportArtifactStore(Protocol):
    def get(self, job_id: str) -> ReportArtifact:
        ...


ReportSender = Callable[[ReportArtifact], None]


class ReportDeliveryAccessError(PermissionError):
    """Caller does not own the requested report."""


class ReportDeliveryNotReadyError(ValueError):
    """Report cannot be delivered before export completion."""



class ReportDeliveryService:
    """Deliver report bytes and release billing only after successful transport."""

    def __init__(
        self,
        billing: ComputeJobBillingStore,
        reports: ReportArtifactStore,
        payments=None,
        jobs=None,
    ) -> None:
        self._billing = billing
        self._reports = reports
        self._payments = payments
        self._jobs = jobs

    def retrieve(
        self,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
    ) -> ReportArtifact:
        """Authorize and load a report without recording successful delivery."""
        billing = self._billing.get(job_id)
        delivery = billing.delivery
        if delivery.user_id != user_id or delivery.project_id != project_id:
            raise ReportDeliveryAccessError("report delivery ownership mismatch")
        if not delivery.export_completed:
            raise ReportDeliveryNotReadyError("report is unavailable until export is completed")
        if self._jobs is not None:
            try:
                job = self._jobs.get(job_id)
            except KeyError as exc:
                raise ReportDeliveryNotReadyError("report delivery requires a completed compute job") from exc
            if job.user_id != user_id or job.project_id != project_id:
                raise ReportDeliveryAccessError("report compute job ownership mismatch")
            if job.status is not ComputeJobStatus.COMPLETED:
                raise ReportDeliveryNotReadyError("report delivery requires a completed compute job")
        if self._payments is not None:
            try:
                payment = self._payments.get_for_job(job_id)
            except KeyError as exc:
                raise ReportDeliveryNotReadyError("report delivery requires a paid order") from exc
            if payment.user_id != user_id or payment.project_id != project_id:
                raise ReportDeliveryAccessError("report payment ownership mismatch")

        report = self._reports.get(job_id)
        if report.job_id != job_id:
            raise ValueError("report artifact does not belong to compute job")
        return report

    def deliver(
        self,
        job_id: str,
        *,
        user_id: str,
        project_id: str,
        send: ReportSender,
    ) -> ComputeJobBilling:
        """Send an authorized report, then persist evidence and release billing.

        The sender must return only after the report has been delivered
        successfully. If it raises, no retrieval evidence or billing release is
        persisted.
        """
        report = self.retrieve(
            job_id,
            user_id=user_id,
            project_id=project_id,
        )
        send(report)

        delivered = self._billing.mark_report_retrieved(
            job_id,
            user_id,
            project_id,
        )
        if delivered.billing_released:
            return delivered
        try:
            return self._billing.release(job_id, user_id, project_id)
        except ValueError as exc:
            # Another successful delivery may have released billing after our
            # evidence write. Treat that race as an idempotent success.
            current = self._billing.get(job_id)
            if current.billing_released:
                return current
            raise exc
