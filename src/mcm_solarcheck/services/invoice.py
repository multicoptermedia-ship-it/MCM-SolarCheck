"""Immutable invoice facts derived from authoritative billing and payment state."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.billing import ComputeJobBillingStore
from mcm_solarcheck.services.payment import OnlinePaymentStore, PaymentAmount


@dataclass(frozen=True)
class InvoiceBasis:
    invoice_id: str
    payment_id: str
    job_id: str
    user_id: str
    project_id: str
    amount: PaymentAmount | None

    def __post_init__(self) -> None:
        for name, value in (
            ("invoice_id", self.invoice_id),
            ("payment_id", self.payment_id),
            ("job_id", self.job_id),
            ("user_id", self.user_id),
            ("project_id", self.project_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")


class InvoiceBasisService:
    """Build invoice facts only after report delivery and billing release."""

    def __init__(
        self,
        billing: ComputeJobBillingStore,
        payments: OnlinePaymentStore,
    ) -> None:
        self._billing = billing
        self._payments = payments

    def build(
        self,
        invoice_id: str,
        payment_id: str,
        *,
        job_id: str,
        user_id: str,
        project_id: str,
    ) -> InvoiceBasis:
        billing = self._billing.get(job_id)
        if (
            billing.delivery.user_id != user_id
            or billing.delivery.project_id != project_id
        ):
            raise PermissionError("invoice billing ownership mismatch")
        if not billing.delivery.billable:
            raise ValueError("invoice requires completed report delivery")
        if not billing.billing_released:
            raise ValueError("invoice requires billing release")

        payment = self._payments.get(payment_id)
        if (
            payment.job_id != job_id
            or payment.user_id != user_id
            or payment.project_id != project_id
        ):
            raise PermissionError("invoice payment identity mismatch")

        return InvoiceBasis(
            invoice_id.strip(),
            payment.payment_id,
            payment.job_id,
            payment.user_id,
            payment.project_id,
            payment.amount,
        )
