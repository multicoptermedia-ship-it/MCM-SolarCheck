"""Archive generated invoices and send an administrative copy."""

from __future__ import annotations

from typing import Protocol

from mcm_solarcheck.infrastructure.filesystem_invoice import FileSystemInvoiceArchive
from mcm_solarcheck.services.admin_notification import ADMIN_NOTIFICATION_EMAIL
from mcm_solarcheck.services.email import EmailAttachment, EmailMessage, EmailSender


class InvoiceAdminDeliveryStateStore(Protocol):
    def claim(self, invoice_id: str) -> bool:
        ...

    def mark_sent(self, invoice_id: str) -> None:
        ...

    def release(self, invoice_id: str) -> None:
        ...


class InvoiceAdminDeliveryService:
    """Persist an existing invoice PDF and send the same bytes to operations."""

    def __init__(
        self,
        archive: FileSystemInvoiceArchive,
        sender: EmailSender,
        *,
        sender_address: str,
        delivery_state: InvoiceAdminDeliveryStateStore | None = None,
    ) -> None:
        self._archive = archive
        self._sender = sender
        self._sender_address = sender_address
        self._delivery_state = delivery_state

    def package_is_ready(self, invoice_id: str) -> bool:
        return self._archive.package_is_ready(invoice_id)

    def deliver(self, invoice_id: str, pdf: bytes, csv_content: bytes | None = None) -> None:
        if csv_content is None:
            path = self._archive.store(invoice_id, pdf)
            csv_path = None
        else:
            path, csv_path = self._archive.store_package(invoice_id, pdf, csv_content)
        if self._delivery_state is not None and not self._delivery_state.claim(invoice_id):
            return
        try:
            self._sender.send(
                EmailMessage(
                    sender=self._sender_address,
                    recipient=ADMIN_NOTIFICATION_EMAIL,
                    subject=f"SolarCheck Rechnung {invoice_id}",
                    text=(
                        "Eine SolarCheck-Rechnung wurde erstellt und im privaten "
                        "Rechnungsarchiv abgelegt.\n"
                        f"Rechnung: {path.name}\n"
                        + (f"Begleitdatei: {csv_path.name}\n" if csv_path is not None else "")
                    ),
                    attachments=(
                        EmailAttachment(path.name, pdf, "application/pdf"),
                    ),
                )
            )
        except Exception:
            if self._delivery_state is not None:
                self._delivery_state.release(invoice_id)
            raise
        if self._delivery_state is not None:
            self._delivery_state.mark_sent(invoice_id)
