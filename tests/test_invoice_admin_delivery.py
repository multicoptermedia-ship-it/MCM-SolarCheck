from __future__ import annotations

import sqlite3

import pytest

from mcm_solarcheck.infrastructure.filesystem_invoice import FileSystemInvoiceArchive
from mcm_solarcheck.infrastructure.sqlite_invoice_admin_delivery import (
    SQLiteInvoiceAdminDeliveryStore,
)
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


class FailingOnceEmailSender(RecordingEmailSender):
    def __init__(self) -> None:
        super().__init__()
        self.fail = True

    def send(self, message: EmailMessage) -> None:
        if self.fail:
            self.fail = False
            raise OSError("SMTP unavailable")
        super().send(message)


def test_invoice_admin_delivery_retry_keeps_archive_and_sends_once(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    sender = FailingOnceEmailSender()
    state = SQLiteInvoiceAdminDeliveryStore(tmp_path / "invoice-delivery.sqlite")
    service = InvoiceAdminDeliveryService(
        archive,
        sender,
        sender_address="solarcheck@mcm-solarcheck.de",
        delivery_state=state,
    )
    pdf = b"%PDF invoice"

    with pytest.raises(OSError, match="SMTP unavailable"):
        service.deliver("invoice-42", pdf)

    assert archive.path_for("invoice-42").read_bytes() == pdf

    service.deliver("invoice-42", pdf)
    service.deliver("invoice-42", pdf)

    assert len(sender.messages) == 1
    assert sender.messages[0].attachments[0].content == pdf


def test_invoice_admin_delivery_active_lease_blocks_parallel_email(tmp_path) -> None:
    database = tmp_path / "invoice-delivery.sqlite"
    first = SQLiteInvoiceAdminDeliveryStore(database)
    second = SQLiteInvoiceAdminDeliveryStore(database)

    assert first.claim("invoice-42") is True
    assert second.claim("invoice-42") is False


def test_expired_invoice_admin_delivery_lease_is_recoverable_after_restart(tmp_path) -> None:
    database = tmp_path / "invoice-delivery.sqlite"
    first = SQLiteInvoiceAdminDeliveryStore(database)
    assert first.claim("invoice-42") is True

    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            UPDATE invoice_admin_delivery
            SET lease_until = 0
            WHERE invoice_id = ?
            """,
            ("invoice-42",),
        )

    restarted = SQLiteInvoiceAdminDeliveryStore(database)
    assert restarted.claim("invoice-42") is True
    restarted.mark_sent("invoice-42")

    assert SQLiteInvoiceAdminDeliveryStore(database).claim("invoice-42") is False


def test_sent_invoice_admin_email_is_not_resent_after_service_restart(tmp_path) -> None:
    database = tmp_path / "invoice-delivery.sqlite"
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    sender = RecordingEmailSender()
    pdf = b"%PDF invoice"

    first = InvoiceAdminDeliveryService(
        archive,
        sender,
        sender_address="solarcheck@mcm-solarcheck.de",
        delivery_state=SQLiteInvoiceAdminDeliveryStore(database),
    )
    first.deliver("invoice-42", pdf)

    restarted = InvoiceAdminDeliveryService(
        archive,
        sender,
        sender_address="solarcheck@mcm-solarcheck.de",
        delivery_state=SQLiteInvoiceAdminDeliveryStore(database),
    )
    restarted.deliver("invoice-42", pdf)

    assert len(sender.messages) == 1
    assert archive.path_for("invoice-42").read_bytes() == pdf


def test_invoice_id_cannot_replace_archived_pdf_with_different_content(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    original = b"%PDF original"
    archive.store("invoice-42", original)

    with pytest.raises(ValueError, match="different content"):
        archive.store("invoice-42", b"%PDF changed")

    assert archive.path_for("invoice-42").read_bytes() == original


def test_invoice_package_retry_requires_identical_pdf_and_csv(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    pdf = b"%PDF original"
    csv_content = b"invoice_id;item_number\ninvoice-42;81011\n"
    archive.store_package("invoice-42", pdf, csv_content)

    assert archive.store_package("invoice-42", pdf, csv_content) == (
        archive.path_for("invoice-42"),
        archive.csv_path_for("invoice-42"),
    )

    with pytest.raises(ValueError, match="different content"):
        archive.store_package("invoice-42", pdf, b"changed csv")

    assert archive.path_for("invoice-42").read_bytes() == pdf
    assert archive.csv_path_for("invoice-42").read_bytes() == csv_content
