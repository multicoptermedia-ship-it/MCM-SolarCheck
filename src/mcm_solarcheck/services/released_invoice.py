"""Gate invoice archival and admin delivery on authoritative billing release."""

from __future__ import annotations

from mcm_solarcheck.services.billing import ComputeJobBillingStore
from mcm_solarcheck.services.invoice_admin_delivery import InvoiceAdminDeliveryService


class ReleasedInvoiceService:
    """Accept a completed invoice document only for released delivered work."""

    def __init__(
        self,
        billing: ComputeJobBillingStore,
        delivery: InvoiceAdminDeliveryService,
    ) -> None:
        self._billing = billing
        self._delivery = delivery

    def deliver(
        self,
        invoice_id: str,
        pdf: bytes,
        *,
        csv_content: bytes | None = None,
        job_id: str,
        user_id: str,
        project_id: str,
    ) -> None:
        state = self._billing.get(job_id)
        if (
            state.delivery.user_id != user_id
            or state.delivery.project_id != project_id
        ):
            raise PermissionError("invoice billing ownership mismatch")
        if not state.delivery.billable:
            raise ValueError("invoice requires completed report delivery")
        if not state.billing_released:
            raise ValueError("invoice requires billing release")
        self._delivery.deliver(invoice_id, pdf, csv_content)
