import pytest

from mcm_solarcheck.infrastructure.sqlite_recovery_grants import SQLiteRecoveryGrants
from mcm_solarcheck.infrastructure.sqlite_audited_recovery_grants import SQLiteAuditedRecoveryGrants


def test_legacy_grant_setter_fails_closed(tmp_path):
    db = tmp_path / "grants.db"
    legacy = SQLiteRecoveryGrants(db)
    with pytest.raises(PermissionError, match="unaudited"):
        legacy.set_grant("op", "c", "p", True)
    assert not legacy.allowed("op", "c", "p")


def test_legacy_reader_sees_audited_changes(tmp_path):
    db = tmp_path / "grants.db"
    legacy = SQLiteRecoveryGrants(db)
    audited = SQLiteAuditedRecoveryGrants(db)
    audited.set_grant("admin", "op", "c", "p", True)
    assert legacy.allowed("op", "c", "p")
    audited.set_grant("admin", "op", "c", "p", False)
    assert not legacy.allowed("op", "c", "p")
