from __future__ import annotations

import sqlite3

import pytest

from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig
from mcm_solarcheck.infrastructure.sqlite_smtp_admin_audit import SQLiteSMTPAdminAudit
from mcm_solarcheck.infrastructure.sqlite_smtp_settings import SQLiteSMTPSettingsStore
from mcm_solarcheck.services.smtp_admin import SMTPAdminAuditEvent


def test_sqlite_smtp_admin_audit_appends_fixed_events_with_utc_timestamp(tmp_path) -> None:
    database = tmp_path / "smtp-admin.sqlite"
    audit = SQLiteSMTPAdminAudit(database)

    audit.record(SMTPAdminAuditEvent.SETTINGS_CHANGED)
    audit.record(SMTPAdminAuditEvent.PASSWORD_REPLACED)

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT event, created_at FROM smtp_admin_audit ORDER BY id"
        ).fetchall()

    assert [row[0] for row in rows] == [
        "settings_changed",
        "password_replaced",
    ]
    assert all(timestamp.endswith("Z") for _, timestamp in rows)


def test_sqlite_smtp_admin_audit_rejects_arbitrary_text(tmp_path) -> None:
    audit = SQLiteSMTPAdminAudit(tmp_path / "smtp-admin.sqlite")

    with pytest.raises(TypeError, match="SMTPAdminAuditEvent"):
        audit.record("password=must-never-be-stored")  # type: ignore[arg-type]

    with sqlite3.connect(audit.database) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM smtp_admin_audit"
        ).fetchone()[0]

    assert count == 0


def test_sqlite_smtp_admin_audit_schema_contains_no_smtp_secret_fields(tmp_path) -> None:
    database = tmp_path / "smtp-admin.sqlite"
    SQLiteSMTPAdminAudit(database)

    with sqlite3.connect(database) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(smtp_admin_audit)")
        }

    assert columns == {"id", "event", "created_at"}


def test_smtp_settings_and_admin_audit_share_database_without_secrets(tmp_path) -> None:
    database = tmp_path / "solarcheck.sqlite"
    settings = SQLiteSMTPSettingsStore(
        database,
        SMTPConfig("smtp.example.com", 587, "solarcheck@mcm-dronetech.com"),
    )
    audit = SQLiteSMTPAdminAudit(database)

    settings.save(
        SMTPConfig("smtp.example.com", 587, "solarcheck@mcm-dronetech.com")
    )
    audit.record(SMTPAdminAuditEvent.SETTINGS_CHANGED)

    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        settings_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(smtp_settings)")
        }
        audit_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(smtp_admin_audit)")
        }
        event = connection.execute(
            "SELECT event FROM smtp_admin_audit ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]

    assert {"smtp_settings", "smtp_admin_audit"} <= tables
    assert "password" not in settings_columns
    assert "secret" not in settings_columns
    assert audit_columns == {"id", "event", "created_at"}
    assert event == SMTPAdminAuditEvent.SETTINGS_CHANGED.value


def test_smtp_admin_persistence_survives_store_restart(tmp_path) -> None:
    database = tmp_path / "solarcheck.sqlite"
    default = SMTPConfig(
        "smtp.initial.example",
        587,
        "solarcheck@mcm-dronetech.com",
    )
    settings = SQLiteSMTPSettingsStore(database, default)
    audit = SQLiteSMTPAdminAudit(database)
    changed = SMTPConfig(
        "smtp.changed.example",
        465,
        "smtp-login",
        timeout_seconds=15.0,
        security=__import__(
            "mcm_solarcheck.infrastructure.smtp_email",
            fromlist=["SMTPSecurity"],
        ).SMTPSecurity.TLS,
        sender_address="solarcheck@mcm-dronetech.com",
    )

    settings.save(changed)
    audit.record(SMTPAdminAuditEvent.SETTINGS_CHANGED)

    restarted_settings = SQLiteSMTPSettingsStore(database, default)
    SQLiteSMTPAdminAudit(database)
    loaded = restarted_settings.get()

    with sqlite3.connect(database) as connection:
        events = connection.execute(
            "SELECT event FROM smtp_admin_audit ORDER BY id"
        ).fetchall()

    assert loaded.host == "smtp.changed.example"
    assert loaded.port == 465
    assert loaded.username == "smtp-login"
    assert loaded.effective_sender_address == "solarcheck@mcm-dronetech.com"
    assert [row[0] for row in events] == ["settings_changed"]
