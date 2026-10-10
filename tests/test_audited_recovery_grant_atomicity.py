import sqlite3

import pytest

from mcm_solarcheck.infrastructure.sqlite_audited_recovery_grants import SQLiteAuditedRecoveryGrants


def test_audit_insert_failure_rolls_back_grant(tmp_path):
    db = tmp_path / "grants.db"
    grants = SQLiteAuditedRecoveryGrants(db)
    with sqlite3.connect(db) as connection:
        connection.execute("""CREATE TRIGGER reject_grant_audit BEFORE INSERT ON recovery_grant_events
            BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="audit unavailable"):
        grants.set_grant("admin", "op", "c", "p", True)
    assert not grants.allowed("op", "c", "p")
    assert grants.list_events("op", "c", "p") == []


def test_invalid_grant_identity_never_writes(tmp_path):
    grants = SQLiteAuditedRecoveryGrants(tmp_path / "grants.db")
    with pytest.raises(ValueError):
        grants.set_grant("admin", "", "c", "p", True)
    with pytest.raises(ValueError):
        grants.set_grant("admin", "op", "c", "p", 1)
    assert grants.list_events("op", "c", "p") == []
