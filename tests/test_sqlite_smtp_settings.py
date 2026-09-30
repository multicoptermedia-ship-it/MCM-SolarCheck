from __future__ import annotations

import sqlite3

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig
from mcm_solarcheck.infrastructure.sqlite_smtp_settings import SQLiteSMTPSettingsStore


def test_smtp_settings_use_safe_default_then_persist_admin_changes(tmp_path) -> None:
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
        2525,
        "solarcheck@mcm-dronetech.com",
        False,
        15.0,
    )
    store.save(changed)

    assert SQLiteSMTPSettingsStore(database, default).get() == changed


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
    assert row is not None
    assert all("password" not in str(value).lower() for value in row)
