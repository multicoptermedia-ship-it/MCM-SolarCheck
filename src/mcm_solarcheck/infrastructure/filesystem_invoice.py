"""Private filesystem archive for generated invoice documents."""

from __future__ import annotations

from pathlib import Path


class FileSystemInvoiceArchive:
    """Store invoices below one configured private SFTP-managed directory."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    @staticmethod
    def _safe_invoice_id(invoice_id: str) -> str:
        if not isinstance(invoice_id, str) or not invoice_id.strip():
            raise ValueError("invoice_id must be non-empty")
        value = invoice_id.strip()
        if value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("invoice_id contains unsafe path characters")
        return value

    def path_for(self, invoice_id: str) -> Path:
        return self.root / f"{self._safe_invoice_id(invoice_id)}.pdf"

    def store(self, invoice_id: str, content: bytes) -> Path:
        if not isinstance(content, bytes) or not content:
            raise ValueError("invoice content must be non-empty bytes")
        path = self.path_for(invoice_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path
