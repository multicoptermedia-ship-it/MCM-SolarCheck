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
        delivery_state=SQLiteInvoiceAdminDeliveryStore(tmp_path / "invoice-delivery.sqlite"),
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
        delivery_state=SQLiteInvoiceAdminDeliveryStore(tmp_path / "invoice-delivery.sqlite"),
    )

    with pytest.raises(ValueError, match="non-empty"):
        service.deliver("invoice-42", b"")

    assert sender.messages == []


def test_invoice_package_archives_pdf_and_csv_but_emails_only_pdf(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    sender = RecordingEmailSender()
    service = InvoiceAdminDeliveryService(
        archive, sender, sender_address="solarcheck@mcm-solarcheck.de",
        delivery_state=SQLiteInvoiceAdminDeliveryStore(tmp_path / "invoice-delivery.sqlite"),
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

    assert first.claim("invoice-42") is not None
    assert second.claim("invoice-42") is None


def test_expired_invoice_admin_delivery_lease_is_recoverable_after_restart(tmp_path) -> None:
    database = tmp_path / "invoice-delivery.sqlite"
    first = SQLiteInvoiceAdminDeliveryStore(database)
    first_token = first.claim("invoice-42")
    assert first_token is not None

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
    restarted_token = restarted.claim("invoice-42")
    assert restarted_token is not None
    restarted.mark_sending("invoice-42", restarted_token)
    restarted.mark_sent("invoice-42", restarted_token)

    assert SQLiteInvoiceAdminDeliveryStore(database).claim("invoice-42") is None


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


def test_invoice_package_ready_marker_exists_only_after_complete_package(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    pdf = b"%PDF invoice"
    csv_content = b"invoice_id;item_number\ninvoice-42;81011\n"

    assert archive.package_is_ready("invoice-42") is False

    archive.store_package("invoice-42", pdf, csv_content)

    assert archive.path_for("invoice-42").read_bytes() == pdf
    assert archive.csv_path_for("invoice-42").read_bytes() == csv_content
    assert archive.package_is_ready("invoice-42") is True
    assert archive.ready_path_for("invoice-42").read_bytes() == b"ready\n"


def test_matching_pdf_only_crash_state_is_completed_on_retry(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    pdf = b"%PDF invoice"
    csv_content = b"invoice_id;item_number\ninvoice-42;81011\n"
    archive.store("invoice-42", pdf)

    archive.store_package("invoice-42", pdf, csv_content)

    assert archive.path_for("invoice-42").read_bytes() == pdf
    assert archive.csv_path_for("invoice-42").read_bytes() == csv_content
    assert archive.package_is_ready("invoice-42") is True


def test_matching_csv_only_crash_state_is_completed_on_retry(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    pdf = b"%PDF invoice"
    csv_content = b"invoice_id;item_number\ninvoice-42;81011\n"
    archive._atomic_write(archive.csv_path_for("invoice-42"), csv_content)

    archive.store_package("invoice-42", pdf, csv_content)

    assert archive.path_for("invoice-42").read_bytes() == pdf
    assert archive.csv_path_for("invoice-42").read_bytes() == csv_content
    assert archive.package_is_ready("invoice-42") is True


def test_mismatched_partial_invoice_package_is_rejected(tmp_path) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    archive.store("invoice-42", b"%PDF different")

    with pytest.raises(ValueError, match="different content"):
        archive.store_package(
            "invoice-42",
            b"%PDF expected",
            b"invoice_id;item_number\ninvoice-42;81011\n",
        )

    assert archive.path_for("invoice-42").read_bytes() == b"%PDF different"
    assert archive.csv_path_for("invoice-42").exists() is False
    assert archive.package_is_ready("invoice-42") is False


@pytest.mark.parametrize("missing_component", ["pdf", "csv"])
def test_ready_marker_requires_both_invoice_package_components(
    tmp_path, missing_component
) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    invoice_id = "invoice-42"
    archive.root.mkdir(parents=True, exist_ok=True)
    archive.ready_path_for(invoice_id).write_bytes(b"ready\n")

    if missing_component != "pdf":
        archive.path_for(invoice_id).write_bytes(b"%PDF invoice")
    if missing_component != "csv":
        archive.csv_path_for(invoice_id).write_bytes(
            b"invoice_id;item_number\ninvoice-42;81011\n"
        )

    assert archive.package_is_ready(invoice_id) is False


@pytest.mark.parametrize("missing_component", ["pdf", "csv"])
def test_retry_repairs_package_with_stale_ready_marker(
    tmp_path, missing_component
) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    invoice_id = "invoice-42"
    pdf = b"%PDF invoice"
    csv_content = b"invoice_id;item_number\ninvoice-42;81011\n"
    archive.root.mkdir(parents=True, exist_ok=True)
    archive.ready_path_for(invoice_id).write_bytes(b"ready\n")

    if missing_component != "pdf":
        archive.path_for(invoice_id).write_bytes(pdf)
    if missing_component != "csv":
        archive.csv_path_for(invoice_id).write_bytes(csv_content)

    assert archive.package_is_ready(invoice_id) is False

    archive.store_package(invoice_id, pdf, csv_content)

    assert archive.path_for(invoice_id).read_bytes() == pdf
    assert archive.csv_path_for(invoice_id).read_bytes() == csv_content
    assert archive.package_is_ready(invoice_id) is True


@pytest.mark.parametrize("mismatched_component", ["pdf", "csv"])
def test_stale_ready_marker_never_allows_invoice_content_replacement(
    tmp_path, mismatched_component
) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    invoice_id = "invoice-42"
    expected_pdf = b"%PDF expected"
    expected_csv = b"invoice_id;item_number\ninvoice-42;81011\n"
    wrong_pdf = b"%PDF different"
    wrong_csv = b"invoice_id;item_number\ninvoice-42;99999\n"
    archive.root.mkdir(parents=True, exist_ok=True)
    archive.ready_path_for(invoice_id).write_bytes(b"ready\n")

    archive.path_for(invoice_id).write_bytes(
        wrong_pdf if mismatched_component == "pdf" else expected_pdf
    )
    archive.csv_path_for(invoice_id).write_bytes(
        wrong_csv if mismatched_component == "csv" else expected_csv
    )

    with pytest.raises(ValueError, match="different content"):
        archive.store_package(invoice_id, expected_pdf, expected_csv)

    assert archive.path_for(invoice_id).read_bytes() == (
        wrong_pdf if mismatched_component == "pdf" else expected_pdf
    )
    assert archive.csv_path_for(invoice_id).read_bytes() == (
        wrong_csv if mismatched_component == "csv" else expected_csv
    )


@pytest.mark.parametrize(
    "delivery_state,message",
    [
        (None, "delivery_state must provide claim"),
        (
            type("State", (), {"claim": lambda self, invoice_id: "token"})(),
            "delivery_state must provide mark_sending",
        ),
        (
            type(
                "State",
                (),
                {
                    "claim": lambda self, invoice_id: "token",
                    "mark_sending": lambda self, invoice_id, claim_token: None,
                    "mark_sent": lambda self, invoice_id, claim_token: None,
                },
            )(),
            "delivery_state must provide release",
        ),
    ],
)
def test_invoice_admin_delivery_rejects_incomplete_state_wiring(
    tmp_path, delivery_state, message
) -> None:
    with pytest.raises(TypeError, match=message):
        InvoiceAdminDeliveryService(
            FileSystemInvoiceArchive(tmp_path / "private" / "invoices"),
            RecordingEmailSender(),
            sender_address="solarcheck@mcm-solarcheck.de",
            delivery_state=delivery_state,  # type: ignore[arg-type]
        )


def test_expired_invoice_delivery_claim_cannot_mutate_new_owner(tmp_path) -> None:
    database = tmp_path / "invoice-delivery.sqlite"
    old_worker = SQLiteInvoiceAdminDeliveryStore(database)
    old_token = old_worker.claim("invoice-42")
    assert old_token is not None

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE invoice_admin_delivery SET lease_until = 0 WHERE invoice_id = ?",
            ("invoice-42",),
        )

    new_worker = SQLiteInvoiceAdminDeliveryStore(database)
    new_token = new_worker.claim("invoice-42")
    assert new_token is not None
    assert new_token != old_token

    with pytest.raises(ValueError, match="not sending"):
        old_worker.mark_sent("invoice-42", old_token)
    with pytest.raises(ValueError, match="not owned"):
        old_worker.release("invoice-42", old_token)

    assert SQLiteInvoiceAdminDeliveryStore(database).claim("invoice-42") is None
    new_worker.mark_sent("invoice-42", new_token)
    assert SQLiteInvoiceAdminDeliveryStore(database).claim("invoice-42") is None


def test_legacy_invoice_delivery_database_migrates_and_reclaims_expired_lease(
    tmp_path,
) -> None:
    database = tmp_path / "invoice-delivery.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE invoice_admin_delivery (
                invoice_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                lease_until REAL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO invoice_admin_delivery (invoice_id, status, lease_until)
            VALUES (?, 'pending', 0)
            """,
            ("invoice-42",),
        )

    migrated = SQLiteInvoiceAdminDeliveryStore(database)
    token = migrated.claim("invoice-42")

    assert token is not None
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT status, claim_token
            FROM invoice_admin_delivery
            WHERE invoice_id = ?
            """,
            ("invoice-42",),
        ).fetchone()
    assert row == ("pending", token)

    migrated.mark_sending("invoice-42", token)
    migrated.mark_sent("invoice-42", token)
    assert SQLiteInvoiceAdminDeliveryStore(database).claim("invoice-42") is None


def test_legacy_active_invoice_delivery_lease_remains_locked_after_migration(
    tmp_path,
) -> None:
    database = tmp_path / "invoice-delivery.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE invoice_admin_delivery (
                invoice_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                lease_until REAL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO invoice_admin_delivery (invoice_id, status, lease_until)
            VALUES (?, 'pending', ?)
            """,
            ("invoice-42", 4102444800.0),
        )

    migrated = SQLiteInvoiceAdminDeliveryStore(database)

    assert migrated.claim("invoice-42") is None
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT status, claim_token
            FROM invoice_admin_delivery
            WHERE invoice_id = ?
            """,
            ("invoice-42",),
        ).fetchone()
    assert row == ("pending", None)


class MarkSentFailingState:
    def __init__(self) -> None:
        self.released = False

    def claim(self, invoice_id: str) -> str | None:
        return "owned-token"

    def mark_sending(self, invoice_id: str, claim_token: str) -> None:
        pass

    def mark_sent(self, invoice_id: str, claim_token: str) -> None:
        raise OSError("delivery state unavailable")

    def release(self, invoice_id: str, claim_token: str) -> None:
        self.released = True


def test_successful_invoice_email_does_not_release_claim_if_mark_sent_fails(
    tmp_path,
) -> None:
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    sender = RecordingEmailSender()
    state = MarkSentFailingState()
    service = InvoiceAdminDeliveryService(
        archive,
        sender,
        sender_address="solarcheck@mcm-solarcheck.de",
        delivery_state=state,
    )

    with pytest.raises(OSError, match="delivery state unavailable"):
        service.deliver("invoice-42", b"%PDF invoice")

    assert len(sender.messages) == 1
    assert state.released is False


def test_invoice_delivery_state_transitions_release_retry_then_sent_lock(
    tmp_path,
) -> None:
    database = tmp_path / "invoice-delivery.sqlite"
    state = SQLiteInvoiceAdminDeliveryStore(database)

    failed_attempt = state.claim("invoice-42")
    assert failed_attempt is not None
    state.mark_sending("invoice-42", failed_attempt)
    state.release("invoice-42", failed_attempt)

    retry = SQLiteInvoiceAdminDeliveryStore(database).claim("invoice-42")
    assert retry is not None
    assert retry != failed_attempt
    SQLiteInvoiceAdminDeliveryStore(database).mark_sending("invoice-42", retry)
    SQLiteInvoiceAdminDeliveryStore(database).mark_sent("invoice-42", retry)

    restarted = SQLiteInvoiceAdminDeliveryStore(database)
    assert restarted.claim("invoice-42") is None
    with pytest.raises(ValueError, match="not owned"):
        restarted.release("invoice-42", retry)
    with pytest.raises(ValueError, match="not sending"):
        restarted.mark_sent("invoice-42", retry)


class SendAndReleaseFailingState:
    def claim(self, invoice_id: str) -> str | None:
        return "expired-token"

    def mark_sending(self, invoice_id: str, claim_token: str) -> None:
        pass

    def mark_sent(self, invoice_id: str, claim_token: str) -> None:
        raise AssertionError("failed SMTP send must not be marked sent")

    def release(self, invoice_id: str, claim_token: str) -> None:
        raise ValueError("invoice admin delivery claim is not owned")


class AlwaysFailingEmailSender:
    def send(self, message: EmailMessage) -> None:
        raise OSError("SMTP unavailable")


def test_lost_lease_during_failed_invoice_email_preserves_smtp_error(tmp_path) -> None:
    service = InvoiceAdminDeliveryService(
        FileSystemInvoiceArchive(tmp_path / "private" / "invoices"),
        AlwaysFailingEmailSender(),
        sender_address="solarcheck@mcm-solarcheck.de",
        delivery_state=SendAndReleaseFailingState(),
    )

    with pytest.raises(OSError, match="SMTP unavailable"):
        service.deliver("invoice-42", b"%PDF invoice")


def test_successful_email_with_expired_sending_lease_stays_fail_closed(
    tmp_path,
) -> None:
    database = tmp_path / "invoice-delivery.sqlite"
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    sender = RecordingEmailSender()
    state = SQLiteInvoiceAdminDeliveryStore(database)
    service = InvoiceAdminDeliveryService(
        archive,
        sender,
        sender_address="solarcheck@mcm-solarcheck.de",
        delivery_state=state,
    )

    original_mark_sent = state.mark_sent

    def expire_then_mark(invoice_id: str, claim_token: str) -> None:
        with sqlite3.connect(database) as connection:
            connection.execute(
                "UPDATE invoice_admin_delivery SET lease_until = 0 WHERE invoice_id = ?",
                (invoice_id,),
            )
        assert SQLiteInvoiceAdminDeliveryStore(database).claim(invoice_id) is None
        original_mark_sent(invoice_id, claim_token)

    state.mark_sent = expire_then_mark  # type: ignore[method-assign]
    service.deliver("invoice-42", b"%PDF invoice")

    assert len(sender.messages) == 1
    assert SQLiteInvoiceAdminDeliveryStore(database).claim("invoice-42") is None

def test_expired_sending_invoice_is_not_automatically_retried(tmp_path) -> None:
    database = tmp_path / "invoice-delivery.sqlite"
    state = SQLiteInvoiceAdminDeliveryStore(database)
    token = state.claim("invoice-42")
    assert token is not None
    state.mark_sending("invoice-42", token)

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE invoice_admin_delivery SET lease_until = 0 WHERE invoice_id = ?",
            ("invoice-42",),
        )

    restarted = SQLiteInvoiceAdminDeliveryStore(database)
    assert restarted.claim("invoice-42") is None

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT status, claim_token FROM invoice_admin_delivery WHERE invoice_id = ?",
            ("invoice-42",),
        ).fetchone()
    assert row == ("sending", token)
