from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.filesystem_invoice import FileSystemInvoiceArchive
from mcm_solarcheck.infrastructure.sqlite_invoice_admin_delivery import SQLiteInvoiceAdminDeliveryStore
from mcm_solarcheck.infrastructure.sqlite_billing import SQLiteComputeJobBillingStore
from mcm_solarcheck.services.admin_notification import ADMIN_NOTIFICATION_EMAIL
from mcm_solarcheck.services.billing import ComputeJobBillingService
from mcm_solarcheck.services.email import EmailMessage
from mcm_solarcheck.services.invoice_admin_delivery import InvoiceAdminDeliveryService
from mcm_solarcheck.services.released_invoice import ReleasedInvoiceService


class RecordingEmailSender:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


def setup(tmp_path):
    store = SQLiteComputeJobBillingStore(tmp_path / "billing.sqlite")
    billing = ComputeJobBillingService(store)
    billing.create("job-a", user_id="user-a", project_id="project-a")
    archive = FileSystemInvoiceArchive(tmp_path / "private" / "invoices")
    sender = RecordingEmailSender()
    delivery = InvoiceAdminDeliveryService(
        archive, sender, sender_address="solarcheck@mcm-solarcheck.de",
        delivery_state=SQLiteInvoiceAdminDeliveryStore(tmp_path / "invoice-delivery.sqlite"),
    )
    return store, billing, archive, sender, ReleasedInvoiceService(store, delivery)


def test_invoice_blocked_before_successful_report_delivery(tmp_path) -> None:
    _, billing, archive, sender, service = setup(tmp_path)
    billing.mark_export_completed("job-a", user_id="user-a", project_id="project-a")

    with pytest.raises(ValueError, match="report delivery"):
        service.deliver(
            "invoice-a", b"%PDF invoice",
            job_id="job-a", user_id="user-a", project_id="project-a",
        )

    assert archive.path_for("invoice-a").exists() is False
    assert sender.messages == []


def test_invoice_archived_and_emailed_only_after_billing_release(tmp_path) -> None:
    _, billing, archive, sender, service = setup(tmp_path)
    billing.mark_export_completed("job-a", user_id="user-a", project_id="project-a")
    billing.mark_report_retrieved("job-a", user_id="user-a", project_id="project-a")
    billing.release("job-a", user_id="user-a", project_id="project-a")
    pdf = b"%PDF invoice"

    service.deliver(
        "invoice-a", pdf,
        job_id="job-a", user_id="user-a", project_id="project-a",
    )

    assert archive.path_for("invoice-a").read_bytes() == pdf
    assert len(sender.messages) == 1
    assert sender.messages[0].recipient == ADMIN_NOTIFICATION_EMAIL
    assert sender.messages[0].attachments[0].content == pdf


def test_invoice_package_csv_is_also_gated_by_billing_release(tmp_path) -> None:
    _, billing, archive, sender, service = setup(tmp_path)
    billing.mark_export_completed("job-a", user_id="user-a", project_id="project-a")
    csv_content = b"invoice_id;item_number\\ninvoice-a;81011\\n"

    with pytest.raises(ValueError, match="report delivery"):
        service.deliver(
            "invoice-a", b"%PDF invoice", csv_content=csv_content,
            job_id="job-a", user_id="user-a", project_id="project-a",
        )

    assert archive.path_for("invoice-a").exists() is False
    assert archive.csv_path_for("invoice-a").exists() is False
    assert sender.messages == []

    billing.mark_report_retrieved("job-a", user_id="user-a", project_id="project-a")
    billing.release("job-a", user_id="user-a", project_id="project-a")
    service.deliver(
        "invoice-a", b"%PDF invoice", csv_content=csv_content,
        job_id="job-a", user_id="user-a", project_id="project-a",
    )

    assert archive.path_for("invoice-a").is_file()
    assert archive.csv_path_for("invoice-a").read_bytes() == csv_content
    assert len(sender.messages) == 1


@pytest.mark.parametrize(
    "billing,delivery,message",
    [
        (object(), object(), "billing must provide get"),
        (
            type("Billing", (), {"get": lambda self, job_id: None})(),
            object(),
            "delivery must provide package_is_ready",
        ),
        (
            type("Billing", (), {"get": lambda self, job_id: None})(),
            type("Delivery", (), {"package_is_ready": lambda self, invoice_id: False})(),
            "delivery must provide deliver",
        ),
    ],
)
def test_released_invoice_service_rejects_incomplete_wiring(
    billing, delivery, message
) -> None:
    with pytest.raises(TypeError, match=message):
        ReleasedInvoiceService(billing, delivery)  # type: ignore[arg-type]
