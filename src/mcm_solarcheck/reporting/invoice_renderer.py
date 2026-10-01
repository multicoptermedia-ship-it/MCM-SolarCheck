"""Render SolarCheck invoice documents as PDF and machine-readable CSV."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

from mcm_solarcheck.services.invoice import InvoiceDocument


def _money(minor_units: int, currency: str) -> str:
    value = minor_units / 100
    return f"{value:,.2f} {currency}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_invoice_pdf(
    invoice: InvoiceDocument,
    destination: str | Path,
    *,
    company_lines: tuple[str, ...],
    payment_text: str,
) -> Path:
    """Render a restrained Fakturama-like invoice without inventing company data."""
    if not company_lines or any(not line.strip() for line in company_lines):
        raise ValueError("company invoice lines must be configured")
    if not payment_text.strip():
        raise ValueError("invoice payment text must be configured")

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    amount = invoice.basis.amount
    assert amount is not None
    story = [
        Paragraph("<br/>".join(company_lines), styles["BodyText"]),
        Spacer(1, 8 * mm),
        Paragraph("<br/>".join((invoice.customer.name, *invoice.customer.address_lines)), styles["BodyText"]),
        Spacer(1, 8 * mm),
        Paragraph(f"Rechnung {invoice.basis.invoice_id}", styles["Title"]),
        Paragraph(f"Rechnungsdatum: {invoice.invoice_date.strftime('%d.%m.%Y')}", styles["BodyText"]),
        Paragraph(f"Leistungsdatum: {invoice.service_date.strftime('%d.%m.%Y')}", styles["BodyText"]),
        Spacer(1, 6 * mm),
        Table(
            [
                ["Menge", "Artikel", "Leistung", "Einzelpreis", "Preis"],
                [
                    "1",
                    invoice.item_number,
                    invoice.service_name,
                    _money(invoice.net_minor_units, amount.currency),
                    _money(invoice.net_minor_units, amount.currency),
                ],
            ],
            colWidths=[15 * mm, 22 * mm, 75 * mm, 30 * mm, 30 * mm],
        ),
        Spacer(1, 6 * mm),
        Table(
            [
                ["Zwischensumme:", _money(invoice.net_minor_units, amount.currency)],
                [f"MwSt. {invoice.vat_percent}%:", _money(invoice.vat_minor_units, amount.currency)],
                ["Rechnungsbetrag:", _money(invoice.gross_minor_units, amount.currency)],
            ],
            colWidths=[120 * mm, 45 * mm],
        ),
        Spacer(1, 6 * mm),
        Paragraph(payment_text, styles["BodyText"]),
        Paragraph(
            "Leistungsdatum entspricht Rechnungsdatum."
            if invoice.service_date == invoice.invoice_date
            else f"Leistungsdatum: {invoice.service_date.strftime('%d.%m.%Y')}",
            styles["BodyText"],
        ),
    ]
    SimpleDocTemplate(
        str(destination), pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        invariant=1,
    ).build(story)
    return destination


def render_invoice_csv(invoice: InvoiceDocument, destination: str | Path) -> Path:
    """Write a stable semicolon-separated companion record for bookkeeping."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    amount = invoice.basis.amount
    assert amount is not None
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow([
        "invoice_id", "invoice_date", "service_date", "customer_name",
        "customer_address", "item_number", "service_name", "quantity",
        "net_minor_units", "vat_percent", "vat_minor_units",
        "gross_minor_units", "currency", "payment_id", "job_id", "project_id",
    ])
    writer.writerow([
        invoice.basis.invoice_id,
        invoice.invoice_date.isoformat(),
        invoice.service_date.isoformat(),
        invoice.customer.name,
        " | ".join(invoice.customer.address_lines),
        invoice.item_number,
        invoice.service_name,
        1,
        invoice.net_minor_units,
        invoice.vat_percent,
        invoice.vat_minor_units,
        invoice.gross_minor_units,
        amount.currency,
        invoice.basis.payment_id,
        invoice.basis.job_id,
        invoice.basis.project_id,
    ])
    destination.write_text(buffer.getvalue(), encoding="utf-8")
    return destination
