from __future__ import annotations

import sqlite3

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPSecurity
from mcm_solarcheck.infrastructure.sqlite_smtp_settings import SQLiteSMTPSettingsStore


def test_smtp_settings_use_safe_default_then_persist_tls_changes(tmp_path) -> None:
    database = tmp_path / "solarcheck.sqlite"
    default = SMTPConfig(
        "smtp.initial.example",
        587,
        "solarcheck@mcm-dronetech.com",
        True,
        30.0,
    )
    store = SQLiteSMTPSettingsStore(database, default)

    assert store.get() == default

    changed = SMTPConfig(
        "smtp.changed.example",
        465,
        "solarcheck@mcm-dronetech.com",
        timeout_seconds=15.0,
        security=SMTPSecurity.TLS,
    )
    store.save(changed)

    loaded = SQLiteSMTPSettingsStore(database, default).get()
    assert loaded.host == changed.host
    assert loaded.port == 465
    assert loaded.username == changed.username
    assert loaded.timeout_seconds == 15.0
    assert loaded.security_mode is SMTPSecurity.TLS


def test_existing_starttls_row_is_migrated_without_breaking_it(tmp_path) -> None:
    database = tmp_path / "solarcheck.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE smtp_settings (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                username TEXT NOT NULL,
                use_starttls INTEGER NOT NULL,
                timeout_seconds REAL NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO smtp_settings
            (singleton, host, port, username, use_starttls, timeout_seconds)
            VALUES (1, ?, 587, ?, 1, 30.0)
            """,
            ("smtp.legacy.example", "solarcheck@mcm-dronetech.com"),
        )

    store = SQLiteSMTPSettingsStore(
        database,
        SMTPConfig("smtp.default.example", 587, "solarcheck@mcm-dronetech.com"),
    )

    loaded = store.get()
    assert loaded.host == "smtp.legacy.example"
    assert loaded.security_mode is SMTPSecurity.STARTTLS


def test_smtp_settings_database_has_no_password_column_or_secret_value(tmp_path) -> None:
    database = tmp_path / "solarcheck.sqlite"
    store = SQLiteSMTPSettingsStore(
        database,
        SMTPConfig("smtp.example.com", 587, "solarcheck@mcm-dronetech.com"),
    )
    store.save(SMTPConfig("smtp.example.com", 587, "solarcheck@mcm-dronetech.com"))

    with sqlite3.connect(database) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(smtp_settings)")]
        row = connection.execute("SELECT * FROM smtp_settings").fetchone()

    assert "password" not in columns
    assert "secret" not in columns
    assert "security" in columns
    assert row is not None
    assert all("password" not in str(value).lower() for value in row)
