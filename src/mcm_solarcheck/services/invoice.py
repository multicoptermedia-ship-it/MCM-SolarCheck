"""Immutable invoice facts derived from authoritative billing and payment state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from mcm_solarcheck.services.billing import ComputeJobBillingStore
from mcm_solarcheck.services.payment import OnlinePaymentStore, PaymentAmount

SOLARCHECK_ITEM_NUMBER = "81011"
SOLARCHECK_SERVICE_NAME = "SolarCheck – Thermografische Auswertung und Prüfbericht"
STANDARD_VAT_PERCENT = 19


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


@dataclass(frozen=True)
class InvoiceCustomer:
    name: str
    address_lines: tuple[str, ...]
    email: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("invoice customer name must be non-empty")
        if not self.address_lines or any(
            not isinstance(line, str) or not line.strip() for line in self.address_lines
        ):
            raise ValueError("invoice customer address must be complete")


@dataclass(frozen=True)
class InvoiceDocument:
    basis: InvoiceBasis
    customer: InvoiceCustomer
    invoice_date: date
    service_date: date
    item_number: str = SOLARCHECK_ITEM_NUMBER
    service_name: str = SOLARCHECK_SERVICE_NAME
    vat_percent: int = STANDARD_VAT_PERCENT

    def __post_init__(self) -> None:
        if self.basis.amount is None:
            raise ValueError("zero-amount work does not require a payable invoice")
        if self.vat_percent < 0:
            raise ValueError("vat_percent must be non-negative")

    @property
    def gross_minor_units(self) -> int:
        assert self.basis.amount is not None
        return self.basis.amount.minor_units

    @property
    def net_minor_units(self) -> int:
        divisor = Decimal(100 + self.vat_percent) / Decimal(100)
        return int(
            (Decimal(self.gross_minor_units) / divisor).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )

    @property
    def vat_minor_units(self) -> int:
        return self.gross_minor_units - self.net_minor_units


class InvoiceBasisService:
    """Build invoice facts only after report delivery and billing release."""

    def __init__(self, billing: ComputeJobBillingStore, payments: OnlinePaymentStore) -> None:
        self._billing = billing
        self._payments = payments

    def build(
        self, invoice_id: str, payment_id: str, *,
        job_id: str, user_id: str, project_id: str,
    ) -> InvoiceBasis:
        billing = self._billing.get(job_id)
        if billing.delivery.user_id != user_id or billing.delivery.project_id != project_id:
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
            invoice_id.strip(), payment.payment_id, payment.job_id,
            payment.user_id, payment.project_id, payment.amount,
        )
