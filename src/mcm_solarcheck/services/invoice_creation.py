"""Create one consistent invoice package from authoritative state."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from mcm_solarcheck.reporting.invoice_renderer import render_invoice_csv, render_invoice_pdf
from mcm_solarcheck.services.invoice import InvoiceBasisService, InvoiceCustomer, InvoiceDocument
from mcm_solarcheck.services.released_invoice import ReleasedInvoiceService


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
    ) -> None:
        self._basis = basis
        self._released = released
        self._config = config

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
