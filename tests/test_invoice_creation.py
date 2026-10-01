from __future__ import annotations

from datetime import date

import pytest

from mcm_solarcheck.infrastructure.filesystem_invoice import FileSystemInvoiceArchive
from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.infrastructure.sqlite_invoice_identity import SQLiteInvoiceIdentityStore
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.email import EmailMessage
from mcm_solarcheck.services.invoice import InvoiceBasisService, InvoiceCustomer
from mcm_solarcheck.services.invoice_admin_delivery import InvoiceAdminDeliveryService
from mcm_solarcheck.services.invoice_creation import InvoiceCreationService, InvoiceRenderConfig
from mcm_solarcheck.services.payment import OnlinePayment, PaymentAmount
from mcm_solarcheck.services.released_invoice import ReleasedInvoiceService


class PaymentStore:
    def __init__(self, payment: OnlinePayment) -> None:
        self.payment = payment

    def get(self, payment_id: str) -> OnlinePayment:
        if payment_id != self.payment.payment_id:
            raise KeyError(payment_id)
        return self.payment


class Sender:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


def setup_service(tmp_path, *, release: bool):
    billing_store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(billing_store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    billing.mark_export_completed("job-a", user_id="user-a", project_id="project-a")
    if release:
        billing.mark_report_retrieved("job-a", user_id="user-a", project_id="project-a")
        billing.release("job-a", user_id="user-a", project_id="project-a")

    payment = OnlinePayment(
        "payment-a", "user-a", "project-a", "job-a", PaymentAmount(25000, "EUR")
    )
    payments = PaymentStore(payment)
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    sender = Sender()
    admin = InvoiceAdminDeliveryService(
        archive, sender, sender_address="solarcheck@mcm-solarcheck.de"
    )
    released = ReleasedInvoiceService(billing_store, admin)
    service = InvoiceCreationService(
        InvoiceBasisService(billing_store, payments),
        released,
        InvoiceRenderConfig(
            ("MCM-Dronetech GmbH", "Ahornweg 3", "50181 Bedburg"),
            "Bitte überweisen Sie den Rechnungsbetrag.",
        ),
        identity_store=SQLiteInvoiceIdentityStore(tmp_path / "invoice-identity.sqlite"),
    )
    return service, archive, sender


def test_creation_renders_one_consistent_pdf_csv_package_after_release(tmp_path) -> None:
    service, archive, sender = setup_service(tmp_path, release=True)

    invoice = service.create_and_deliver(
        "R20260930-11",
        "payment-a",
        InvoiceCustomer("Testkunde", ("Musterweg 1", "50181 Bedburg")),
        invoice_date=date(2026, 9, 30),
        service_date=date(2026, 9, 30),
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    pdf = archive.path_for("R20260930-11").read_bytes()
    csv_content = archive.csv_path_for("R20260930-11").read_text(encoding="utf-8")
    assert pdf.startswith(b"%PDF")
    assert "81011" in csv_content
    assert "21008" in csv_content
    assert "3992" in csv_content
    assert "25000" in csv_content
    assert invoice.gross_minor_units == 25000
    assert len(sender.messages) == 1
    assert sender.messages[0].attachments[0].content == pdf


def test_creation_produces_no_files_or_email_before_release(tmp_path) -> None:
    service, archive, sender = setup_service(tmp_path, release=False)

    with pytest.raises(ValueError, match="report delivery"):
        service.create_and_deliver(
            "R20260930-11",
            "payment-a",
            InvoiceCustomer("Testkunde", ("Musterweg 1", "50181 Bedburg")),
            invoice_date=date(2026, 9, 30),
            service_date=date(2026, 9, 30),
            job_id="job-a",
            user_id="user-a",
            project_id="project-a",
        )

    assert archive.path_for("R20260930-11").exists() is False
    assert archive.csv_path_for("R20260930-11").exists() is False
    assert sender.messages == []


def test_creation_allows_identical_invoice_retry(tmp_path) -> None:
    service, archive, sender = setup_service(tmp_path, release=True)
    customer = InvoiceCustomer("Testkunde", ("Musterweg 1", "50181 Bedburg"))
    kwargs = dict(
        invoice_date=date(2026, 9, 30),
        service_date=date(2026, 9, 30),
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    first = service.create_and_deliver("R20260930-11", "payment-a", customer, **kwargs)
    second = service.create_and_deliver("R20260930-11", "payment-a", customer, **kwargs)

    assert first == second
    assert archive.package_is_ready("R20260930-11") is True


def test_creation_rejects_reused_invoice_id_for_different_facts(tmp_path) -> None:
    service, archive, sender = setup_service(tmp_path, release=True)
    service.create_and_deliver(
        "R20260930-11",
        "payment-a",
        InvoiceCustomer("Testkunde", ("Musterweg 1", "50181 Bedburg")),
        invoice_date=date(2026, 9, 30),
        service_date=date(2026, 9, 30),
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )
    original_pdf = archive.path_for("R20260930-11").read_bytes()
    original_csv = archive.csv_path_for("R20260930-11").read_bytes()
    original_mail_count = len(sender.messages)

    with pytest.raises(ValueError, match="different invoice facts"):
        service.create_and_deliver(
            "R20260930-11",
            "payment-a",
            InvoiceCustomer("Anderer Kunde", ("Andere Strasse 9", "50181 Bedburg")),
            invoice_date=date(2026, 10, 1),
            service_date=date(2026, 9, 30),
            job_id="job-a",
            user_id="user-a",
            project_id="project-a",
        )

    assert archive.path_for("R20260930-11").read_bytes() == original_pdf
    assert archive.csv_path_for("R20260930-11").read_bytes() == original_csv
    assert archive.package_is_ready("R20260930-11") is True
    assert len(sender.messages) == original_mail_count
