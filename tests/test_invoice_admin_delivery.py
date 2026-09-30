from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.filesystem_invoice import FileSystemInvoiceArchive
from mcm_solarcheck.services.admin_notification import ADMIN_NOTIFICATION_EMAIL
from mcm_solarcheck.services.email import EmailMessage
from mcm_solarcheck.services.invoice_admin_delivery import InvoiceAdminDeliveryService


class RecordingEmailSender:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


def test_invoice_is_archived_privately_and_same_pdf_is_emailed_to_admin(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    sender = RecordingEmailSender()
    service = InvoiceAdminDeliveryService(
        archive,
        sender,
        sender_address="solarcheck@mcm-solarcheck.de",
    )
    pdf = b"%PDF-1.4 invoice"

    service.deliver("invoice-42", pdf)

    path = archive.path_for("invoice-42")
    assert path.read_bytes() == pdf
    assert len(sender.messages) == 1
    message = sender.messages[0]
    assert message.recipient == ADMIN_NOTIFICATION_EMAIL == "solarcheck@mcm-dronetech.com"
    assert len(message.attachments) == 1
    assert message.attachments[0].filename == "invoice-42.pdf"
    assert message.attachments[0].content == pdf
    assert message.attachments[0].media_type == "application/pdf"


@pytest.mark.parametrize("invoice_id", ["../secret", "../../etc/passwd", "nested/id", r"nested\\id", ".", ".."])
def test_invoice_archive_rejects_path_traversal(invoice_id, tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")

    with pytest.raises(ValueError, match="unsafe path"):
        archive.path_for(invoice_id)


def test_invoice_delivery_rejects_empty_document_without_email(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    sender = RecordingEmailSender()
    service = InvoiceAdminDeliveryService(
        archive,
        sender,
        sender_address="solarcheck@mcm-solarcheck.de",
    )

    with pytest.raises(ValueError, match="non-empty"):
        service.deliver("invoice-42", b"")

    assert sender.messages == []


def test_invoice_package_archives_pdf_and_csv_but_emails_only_pdf(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    sender = RecordingEmailSender()
    service = InvoiceAdminDeliveryService(
        archive, sender, sender_address="solarcheck@mcm-solarcheck.de"
    )
    pdf = b"%PDF-1.4 invoice"
    csv_content = b"invoice_id;item_number\\ninvoice-42;81011\\n"

    service.deliver("invoice-42", pdf, csv_content)

    assert archive.path_for("invoice-42").read_bytes() == pdf
    assert archive.csv_path_for("invoice-42").read_bytes() == csv_content
    assert len(sender.messages) == 1
    assert len(sender.messages[0].attachments) == 1
    assert sender.messages[0].attachments[0].filename == "invoice-42.pdf"
    assert "invoice-42.csv" in sender.messages[0].text
    assert list(archive.root.glob("*.tmp")) == []
