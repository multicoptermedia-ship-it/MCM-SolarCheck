import sqlite3

from mcm_solarcheck.infrastructure.sqlite_audited_recovery_grants import SQLiteAuditedRecoveryGrants
from mcm_solarcheck.infrastructure.sqlite_recovery_grants import SQLiteRecoveryGrants
from mcm_solarcheck.services.recovery_grant_audit_coverage import RecoveryGrantAuditCoverage


def test_coverage_finds_preexisting_legacy_grants_and_excludes_audited_grants(tmp_path):
    database = tmp_path / "grants.db"
    SQLiteRecoveryGrants(database)
    audited = SQLiteAuditedRecoveryGrants(database)
    coverage = RecoveryGrantAuditCoverage(database)
    # Simulate a historical database row created before audited writes existed.
    with sqlite3.connect(database) as db:
        db.execute("""INSERT INTO recovery_grants(operator_id,customer_id,project_id,enabled)
            VALUES(?,?,?,?)""", ("legacy", "c", "p", 1))
    audited.set_grant("admin", "audited", "c", "p", True)
    assert coverage.inspect() == [("legacy", "c", "p", 1)]
    audited.set_grant("admin", "legacy", "c", "p", False)
    assert coverage.inspect() == []
