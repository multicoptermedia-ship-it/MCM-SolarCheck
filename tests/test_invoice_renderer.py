from __future__ import annotations

from datetime import date

import pytest

from mcm_solarcheck.reporting.invoice_renderer import render_invoice_csv, render_invoice_pdf
from mcm_solarcheck.services.invoice import (
    InvoiceBasis,
    InvoiceCustomer,
    InvoiceDocument,
    SOLARCHECK_ITEM_NUMBER,
    SOLARCHECK_SERVICE_NAME,
)
from mcm_solarcheck.services.payment import PaymentAmount


def invoice() -> InvoiceDocument:
    return InvoiceDocument(
        InvoiceBasis(
            "R20260930-11", "payment-a", "job-a", "user-a", "project-a",
            PaymentAmount(25000, "EUR"),
        ),
        InvoiceCustomer("Testkunde", ("Musterweg 1", "50181 Bedburg"), "test@example.com"),
        date(2026, 9, 30),
        date(2026, 9, 30),
    )


def test_invoice_matches_solarcheck_article_and_vat_split() -> None:
    value = invoice()
    assert value.item_number == SOLARCHECK_ITEM_NUMBER == "81011"
    assert value.service_name == SOLARCHECK_SERVICE_NAME
    assert value.net_minor_units == 21008
    assert value.vat_minor_units == 3992
    assert value.gross_minor_units == 25000


def test_invoice_requires_explicit_customer_address() -> None:
    with pytest.raises(ValueError, match="address"):
        InvoiceCustomer("Testkunde", ())


def test_invoice_csv_contains_bookkeeping_and_traceability(tmp_path) -> None:
    destination = render_invoice_csv(invoice(), tmp_path / "invoice.csv")
    text = destination.read_text(encoding="utf-8")

    assert "81011" in text
    assert "25000" in text
    assert "3992" in text
    assert "payment-a" in text
    assert "job-a" in text
    assert "project-a" in text


def test_invoice_pdf_is_created_from_explicit_company_configuration(tmp_path) -> None:
    destination = render_invoice_pdf(
        invoice(),
        tmp_path / "invoice.pdf",
        company_lines=("MCM-Dronetech GmbH", "Ahornweg 3", "50181 Bedburg"),
        payment_text="Bitte überweisen Sie den Rechnungsbetrag.",
    )

    assert destination.is_file()
    assert destination.read_bytes().startswith(b"%PDF")


def test_invoice_pdf_rejects_missing_company_configuration(tmp_path) -> None:
    with pytest.raises(ValueError, match="company"):
        render_invoice_pdf(
            invoice(),
            tmp_path / "invoice.pdf",
            company_lines=(),
            payment_text="Bitte überweisen Sie den Rechnungsbetrag.",
        )


def test_invoice_pdf_rendering_is_byte_stable_for_identical_invoice(tmp_path) -> None:
    first = render_invoice_pdf(
        invoice(),
        tmp_path / "first.pdf",
        company_lines=("MCM-Dronetech GmbH", "Ahornweg 3", "50181 Bedburg"),
        payment_text="Bitte überweisen Sie den Rechnungsbetrag.",
    )
    second = render_invoice_pdf(
        invoice(),
        tmp_path / "second.pdf",
        company_lines=("MCM-Dronetech GmbH", "Ahornweg 3", "50181 Bedburg"),
        payment_text="Bitte überweisen Sie den Rechnungsbetrag.",
    )

    assert first.read_bytes() == second.read_bytes()
