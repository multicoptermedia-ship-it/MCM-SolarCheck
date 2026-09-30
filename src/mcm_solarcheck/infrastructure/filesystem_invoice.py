"""Private filesystem archive for generated invoice documents."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class FileSystemInvoiceArchive:
    """Store invoice packages below one configured private SFTP-managed directory."""

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

    def csv_path_for(self, invoice_id: str) -> Path:
        return self.root / f"{self._safe_invoice_id(invoice_id)}.csv"

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def store(self, invoice_id: str, content: bytes) -> Path:
        if not isinstance(content, bytes) or not content:
            raise ValueError("invoice content must be non-empty bytes")
        path = self.path_for(invoice_id)
        self._atomic_write(path, content)
        return path

    def store_package(self, invoice_id: str, pdf: bytes, csv_content: bytes) -> tuple[Path, Path]:
        """Store a finished PDF and its bookkeeping companion in the private archive."""
        if not isinstance(pdf, bytes) or not pdf:
            raise ValueError("invoice content must be non-empty bytes")
        if not isinstance(csv_content, bytes) or not csv_content:
            raise ValueError("invoice csv content must be non-empty bytes")
        pdf_path = self.path_for(invoice_id)
        csv_path = self.csv_path_for(invoice_id)
        self._atomic_write(pdf_path, pdf)
        try:
            self._atomic_write(csv_path, csv_content)
        except Exception:
            pdf_path.unlink(missing_ok=True)
            raise
        return pdf_path, csv_path
