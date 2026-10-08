"""Private filesystem archive for generated invoice documents."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class FileSystemInvoiceArchive:
    """Store invoice packages below one configured private SFTP-managed directory."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._resolved_root = self.root.expanduser().resolve()

    @staticmethod
    def _safe_invoice_id(invoice_id: str) -> str:
        if not isinstance(invoice_id, str) or not invoice_id.strip():
            raise ValueError("invoice_id must be non-empty")
        value = invoice_id.strip()
        if value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("invoice_id contains unsafe path characters")
        return value

    def _private_path(self, filename: str) -> Path:
        path = self.root / filename
        resolved_path = path.resolve()
        try:
            resolved_path.relative_to(self._resolved_root)
        except ValueError as exc:
            raise ValueError("invoice artifact resolves outside configured archive") from exc
        return path

    def path_for(self, invoice_id: str) -> Path:
        return self._private_path(f"{self._safe_invoice_id(invoice_id)}.pdf")

    def csv_path_for(self, invoice_id: str) -> Path:
        return self._private_path(f"{self._safe_invoice_id(invoice_id)}.csv")

    def ready_path_for(self, invoice_id: str) -> Path:
        return self._private_path(f".{self._safe_invoice_id(invoice_id)}.ready")

    def package_is_ready(self, invoice_id: str) -> bool:
        """A release marker is valid only while both package components exist."""
        return (
            self.ready_path_for(invoice_id).is_file()
            and self.path_for(invoice_id).is_file()
            and self.csv_path_for(invoice_id).is_file()
        )

    def _atomic_write(self, path: Path, content: bytes) -> None:
        try:
            path.parent.resolve().relative_to(self._resolved_root)
        except ValueError as exc:
            raise ValueError("invoice artifact resolves outside configured archive") from exc
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
        if path.exists():
            if path.read_bytes() != content:
                raise ValueError("invoice_id already exists with different content")
            return path
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
        ready_path = self.ready_path_for(invoice_id)
        pdf_exists = pdf_path.exists()
        csv_exists = csv_path.exists()
        if pdf_exists or csv_exists:
            if pdf_exists and pdf_path.read_bytes() != pdf:
                raise ValueError("invoice_id already exists with different content")
            if csv_exists and csv_path.read_bytes() != csv_content:
                raise ValueError("invoice_id already exists with different content")
            if not pdf_exists:
                self._atomic_write(pdf_path, pdf)
            if not csv_exists:
                try:
                    self._atomic_write(csv_path, csv_content)
                except Exception:
                    if not pdf_exists:
                        pdf_path.unlink(missing_ok=True)
                    raise
            if not ready_path.is_file():
                self._atomic_write(ready_path, b"ready\n")
            return pdf_path, csv_path

        self._atomic_write(pdf_path, pdf)
        try:
            self._atomic_write(csv_path, csv_content)
        except Exception:
            pdf_path.unlink(missing_ok=True)
            raise
        try:
            self._atomic_write(ready_path, b"ready\n")
        except Exception:
            csv_path.unlink(missing_ok=True)
            pdf_path.unlink(missing_ok=True)
            raise
        return pdf_path, csv_path
