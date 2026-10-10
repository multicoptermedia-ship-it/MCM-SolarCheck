from mcm_solarcheck.infrastructure.sqlite_recovery_attempts import SQLiteRecoveryAttempts
from mcm_solarcheck.infrastructure.sqlite_request_recovery_audit import SQLiteRequestRecoveryAudit
from mcm_solarcheck.services.request_recovery_inspector import RequestRecoveryInspector


class Transfers:
    def get(self, *args):
        return {"state": "pending"}


class Assessment:
    def __init__(self):
        self.calls = 0

    def assess(self, *args):
        self.calls += 1
        return type("Result", (), {"decision": "verified_complete"})()


def test_pending_request_remains_manual_even_if_final_verified(tmp_path):
    db = tmp_path / "audit.db"
    attempts = SQLiteRecoveryAttempts(db)
    audit = SQLiteRequestRecoveryAudit(db)
    assessment = Assessment()
    inspector = RequestRecoveryInspector(attempts, Transfers(), assessment, audit)
    assert attempts.claim("req", "t", "c", "p", "op") == ("new", None)
    audit.record("req", "t", "c", "p", "op", "requested")
    audit.record("other", "t", "c", "p", "op", "journal_reconciled")
    result = inspector.inspect("req", "t", "c", "p", "op")
    assert result.decision == "manual_review_required"
    assert result.assessment_decision == "verified_complete"
    assert result.audit_decisions == ("requested",)
    assert assessment.calls == 1


def test_completed_request_uses_recorded_outcome_without_reverification(tmp_path):
    db = tmp_path / "audit.db"
    attempts = SQLiteRecoveryAttempts(db)
    audit = SQLiteRequestRecoveryAudit(db)
    assessment = Assessment()
    inspector = RequestRecoveryInspector(attempts, Transfers(), assessment, audit)
    attempts.claim("req", "t", "c", "p", "op")
    assert attempts.complete("req", "t", "c", "p", "op", "journal_reconciled")
    result = inspector.inspect("req", "t", "c", "p", "op")
    assert result.decision == "recorded_complete"
    assert result.recorded_outcome == "journal_reconciled"
    assert assessment.calls == 0


def test_foreign_operator_cannot_read_request_audit(tmp_path):
    db = tmp_path / "audit.db"
    attempts = SQLiteRecoveryAttempts(db)
    audit = SQLiteRequestRecoveryAudit(db)
    inspector = RequestRecoveryInspector(attempts, Transfers(), Assessment(), audit)
    attempts.claim("req", "t", "c", "p", "op")
    audit.record("req", "t", "c", "p", "op", "requested")
    assert inspector.inspect("req", "t", "c", "p", "other").decision == "unknown_request"
