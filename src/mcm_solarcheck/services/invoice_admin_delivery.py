"""Archive generated invoices and send an administrative copy."""

from __future__ import annotations

from mcm_solarcheck.infrastructure.filesystem_invoice import FileSystemInvoiceArchive
from mcm_solarcheck.services.admin_notification import ADMIN_NOTIFICATION_EMAIL
from mcm_solarcheck.services.email import EmailAttachment, EmailMessage, EmailSender


class InvoiceAdminDeliveryService:
    """Persist an existing invoice PDF and send the same bytes to operations."""

    def __init__(
        self,
        archive: FileSystemInvoiceArchive,
        sender: EmailSender,
        *,
        sender_address: str,
    ) -> None:
        self._archive = archive
        self._sender = sender
        self._sender_address = sender_address

    def deliver(self, invoice_id: str, pdf: bytes) -> None:
        path = self._archive.store(invoice_id, pdf)
        self._sender.send(
            EmailMessage(
                sender=self._sender_address,
                recipient=ADMIN_NOTIFICATION_EMAIL,
                subject=f"SolarCheck Rechnung {invoice_id}",
                text=(
                    "Eine SolarCheck-Rechnung wurde erstellt und im privaten "
                    "Rechnungsarchiv abgelegt.\n"
                    f"Rechnung: {path.name}\n"
                ),
                attachments=(
                    EmailAttachment(path.name, pdf, "application/pdf"),
                ),
            )
        )
