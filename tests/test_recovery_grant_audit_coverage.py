from mcm_solarcheck.infrastructure.sqlite_audited_recovery_grants import SQLiteAuditedRecoveryGrants
from mcm_solarcheck.infrastructure.sqlite_recovery_grants import SQLiteRecoveryGrants
from mcm_solarcheck.services.recovery_grant_audit_coverage import RecoveryGrantAuditCoverage


def test_coverage_finds_legacy_grants_and_excludes_audited_grants(tmp_path):
    database = tmp_path / "grants.db"
    legacy = SQLiteRecoveryGrants(database)
    audited = SQLiteAuditedRecoveryGrants(database)
    coverage = RecoveryGrantAuditCoverage(database)
    legacy.set_grant("legacy", "c", "p", True)
    audited.set_grant("admin", "audited", "c", "p", True)
    assert coverage.inspect() == [("legacy", "c", "p", 1)]
    audited.set_grant("admin", "legacy", "c", "p", False)
    assert coverage.inspect() == []
