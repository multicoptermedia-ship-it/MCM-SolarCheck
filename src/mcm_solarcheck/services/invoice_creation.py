"""Create one consistent invoice package from authoritative state."""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from mcm_solarcheck.reporting.invoice_renderer import render_invoice_csv, render_invoice_pdf
from mcm_solarcheck.services.invoice import InvoiceBasisService, InvoiceCustomer, InvoiceDocument
from mcm_solarcheck.services.released_invoice import ReleasedInvoiceService


class InvoiceIdentityStore(Protocol):
    def reserve(self, invoice_id: str, fingerprint: str) -> bool:
        ...


@dataclass(frozen=True)
class InvoiceRenderConfig:
    company_lines: tuple[str, ...]
    payment_text: str

    def __post_init__(self) -> None:
        if not self.company_lines or any(
            not isinstance(line, str) or not line.strip() for line in self.company_lines
        ):
            raise ValueError("company invoice lines must be configured")
        if not isinstance(self.payment_text, str) or not self.payment_text.strip():
            raise ValueError("invoice payment text must be configured")


class InvoiceCreationService:
    """Render PDF and CSV from the same facts and deliver them through the release gate."""

    def __init__(
        self,
        basis: InvoiceBasisService,
        released: ReleasedInvoiceService,
        config: InvoiceRenderConfig,
        identity_store: InvoiceIdentityStore | None = None,
    ) -> None:
        self._basis = basis
        self._released = released
        self._config = config
        self._identity_store = identity_store

    def create_and_deliver(
        self,
        invoice_id: str,
        payment_id: str,
        customer: InvoiceCustomer,
        *,
        invoice_date: date,
        service_date: date,
        job_id: str,
        user_id: str,
        project_id: str,
    ) -> InvoiceDocument:
        basis = self._basis.build(
            invoice_id, payment_id,
            job_id=job_id, user_id=user_id, project_id=project_id,
        )
        invoice = InvoiceDocument(basis, customer, invoice_date, service_date)

        if self._identity_store is not None:
            fingerprint_payload = {
                "invoice_id": invoice.basis.invoice_id,
                "payment_id": invoice.basis.payment_id,
                "job_id": invoice.basis.job_id,
                "user_id": invoice.basis.user_id,
                "project_id": invoice.basis.project_id,
                "amount_minor_units": invoice.gross_minor_units,
                "currency": invoice.basis.amount.currency,
                "customer_name": invoice.customer.name,
                "customer_address": list(invoice.customer.address_lines),
                "invoice_date": invoice.invoice_date.isoformat(),
                "service_date": invoice.service_date.isoformat(),
                "item_number": invoice.item_number,
                "service_name": invoice.service_name,
                "vat_percent": invoice.vat_percent,
            }
            fingerprint = hashlib.sha256(
                json.dumps(
                    fingerprint_payload,
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            is_new_identity = self._identity_store.reserve(
                invoice.basis.invoice_id, fingerprint
            )
            if not is_new_identity:
                return invoice

        with tempfile.TemporaryDirectory(prefix="solarcheck-invoice-") as temporary:
            root = Path(temporary)
            pdf_path = render_invoice_pdf(
                invoice,
                root / "invoice.pdf",
                company_lines=self._config.company_lines,
                payment_text=self._config.payment_text,
            )
            csv_path = render_invoice_csv(invoice, root / "invoice.csv")
            pdf = pdf_path.read_bytes()
            csv_content = csv_path.read_bytes()

        self._released.deliver(
            invoice_id,
            pdf,
            csv_content=csv_content,
            job_id=job_id,
            user_id=user_id,
            project_id=project_id,
        )
        return invoice
