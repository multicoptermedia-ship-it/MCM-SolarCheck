from mcm_solarcheck.infrastructure.sqlite_recovery_attempts import SQLiteRecoveryAttempts
from mcm_solarcheck.infrastructure.sqlite_request_recovery_audit import SQLiteRequestRecoveryAudit
from mcm_solarcheck.services.request_recovery_inspector import RequestRecoveryInspector
from mcm_solarcheck.services.request_audited_recovery import RequestAuditedRecovery
from mcm_solarcheck.services.request_scoped_recovery_coordinator import RequestScopedRecoveryCoordinator


class Transfers:
    def get(self, *args):
        return {"state": "pending"}


class Assessment:
    def assess(self, *args):
        return type("AssessmentResult", (), {"decision": "verified_complete"})()


class Recovery:
    def reconcile_verified(self, *args):
        return "journal_reconciled"


def test_inspector_reads_real_coordinator_audit_events(tmp_path):
    db = tmp_path / "recovery.db"
    attempts = SQLiteRecoveryAttempts(db)
    audit = SQLiteRequestRecoveryAudit(db)
    coordinator = RequestScopedRecoveryCoordinator(RequestAuditedRecovery(Recovery(), audit), attempts)
    assert coordinator.reconcile_verified("t", "c", "p", operator_id="op", request_id="req") == "journal_reconciled"
    inspector = RequestRecoveryInspector(attempts, Transfers(), Assessment(), audit)
    review = inspector.inspect("req", "t", "c", "p", "op")
    assert review.decision == "recorded_complete"
    assert review.recorded_outcome == "journal_reconciled"
    assert review.audit_decisions == ("requested", "journal_reconciled")
