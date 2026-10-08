from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.services.smtp_admin import SMTPAdminAuditEvent


class SQLiteSMTPAdminAudit:
    """Append-only persistence for secret-free SMTP administration events."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS smtp_admin_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    )
                )
                """
            )

    def record(self, event: SMTPAdminAuditEvent) -> None:
        if not isinstance(event, SMTPAdminAuditEvent):
            raise TypeError("event must be an SMTPAdminAuditEvent")
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "INSERT INTO smtp_admin_audit (event) VALUES (?)",
                (event.value,),
            )
