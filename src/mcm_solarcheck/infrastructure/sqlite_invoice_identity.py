"""Persistent immutable identity reservation for generated invoices."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteInvoiceIdentityStore:
    """Bind one invoice id permanently to one authoritative invoice fingerprint."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS invoice_identity (
                    invoice_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL
                )
                """
            )

    def reserve(self, invoice_id: str, fingerprint: str) -> bool:
        if not isinstance(invoice_id, str) or not invoice_id.strip():
            raise ValueError("invoice_id must be non-empty")
        if not isinstance(fingerprint, str) or not fingerprint:
            raise ValueError("invoice fingerprint must be non-empty")

        with sqlite3.connect(self.database) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT fingerprint FROM invoice_identity WHERE invoice_id = ?",
                (invoice_id.strip(),),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO invoice_identity (invoice_id, fingerprint)
                    VALUES (?, ?)
                    """,
                    (invoice_id.strip(), fingerprint),
                )
                return True
            if row[0] != fingerprint:
                raise ValueError("invoice_id is already assigned to different invoice facts")
            return False
