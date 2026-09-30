"""SQLite persistence for non-secret SMTP administration settings."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPSecurity


class SQLiteSMTPSettingsStore:
    """Persist only non-secret SMTP settings; passwords never enter this database."""

    def __init__(self, database: str | Path, default: SMTPConfig) -> None:
        self.database = str(database)
        self._default = default
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS smtp_settings (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    use_starttls INTEGER NOT NULL,
                    timeout_seconds REAL NOT NULL
                )
                """
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(smtp_settings)")
            }
            if "security" not in columns:
                connection.execute("ALTER TABLE smtp_settings ADD COLUMN security TEXT")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def get(self) -> SMTPConfig:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT host, port, username, use_starttls, timeout_seconds, security
                FROM smtp_settings
                WHERE singleton = 1
                """
            ).fetchone()
        if row is None:
            return self._default
        security = SMTPSecurity(row[5]) if row[5] else None
        return SMTPConfig(
            host=row[0],
            port=row[1],
            username=row[2],
            use_starttls=bool(row[3]),
            timeout_seconds=row[4],
            security=security,
        )

    def save(self, config: SMTPConfig) -> None:
        security = config.security_mode
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO smtp_settings (
                    singleton, host, port, username, use_starttls, timeout_seconds, security
                ) VALUES (1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(singleton) DO UPDATE SET
                    host = excluded.host,
                    port = excluded.port,
                    username = excluded.username,
                    use_starttls = excluded.use_starttls,
                    timeout_seconds = excluded.timeout_seconds,
                    security = excluded.security
                """,
                (
                    config.host,
                    config.port,
                    config.username,
                    int(security is SMTPSecurity.STARTTLS),
                    config.timeout_seconds,
                    security.value,
                ),
            )
