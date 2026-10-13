from mcm_solarcheck.infrastructure.sqlite_recovery_attempts import SQLiteRecoveryAttempts
from mcm_solarcheck.infrastructure.sqlite_request_recovery_audit import SQLiteRequestRecoveryAudit
from mcm_solarcheck.services.request_audited_recovery import RequestAuditedRecovery
from mcm_solarcheck.services.request_scoped_recovery_coordinator import RequestScopedRecoveryCoordinator


class Recovery:
    def __init__(self):
        self.calls = 0

    def reconcile_verified(self, *args):
        self.calls += 1
        return "journal_reconciled"


def test_end_to_end_request_audit_and_idempotency(tmp_path):
    db = tmp_path / "recovery.db"
    attempts = SQLiteRecoveryAttempts(db)
    audit = SQLiteRequestRecoveryAudit(db)
    recovery = Recovery()
    coordinator = RequestScopedRecoveryCoordinator(RequestAuditedRecovery(recovery, audit), attempts)
    args = ("t", "c", "p")
    assert coordinator.reconcile_verified(*args, operator_id="op", request_id="req") == "journal_reconciled"
    assert coordinator.reconcile_verified(*args, operator_id="op", request_id="req") == "journal_reconciled"
    assert recovery.calls == 1
    assert [event[1] for event in audit.list_for_request("req", *args, "op")] == ["requested", "journal_reconciled"]
    assert coordinator.reconcile_verified(*args, operator_id="other", request_id="req") == "request_identity_conflict"


def test_pre_audit_failure_keeps_attempt_pending_without_execution(tmp_path):
    class FailingAudit:
        def record(self, *args):
            raise OSError("audit offline")

    db = tmp_path / "recovery.db"
    attempts = SQLiteRecoveryAttempts(db)
    recovery = Recovery()
    coordinator = RequestScopedRecoveryCoordinator(RequestAuditedRecovery(recovery, FailingAudit()), attempts)
    try:
        coordinator.reconcile_verified("t", "c", "p", operator_id="op", request_id="req")
        assert False, "audit must fail"
    except OSError:
        pass
    assert recovery.calls == 0
    assert coordinator.reconcile_verified("t", "c", "p", operator_id="op", request_id="req") == "pending_requires_review"


def test_post_audit_failure_leaves_request_ambiguous(tmp_path):
    class SecondWriteFails:
        def __init__(self):
            self.calls = 0

        def record(self, *args):
            self.calls += 1
            if self.calls == 2:
                raise OSError("audit offline")

    db = tmp_path / "recovery.db"
    attempts = SQLiteRecoveryAttempts(db)
    recovery = Recovery()
    coordinator = RequestScopedRecoveryCoordinator(RequestAuditedRecovery(recovery, SecondWriteFails()), attempts)
    try:
        coordinator.reconcile_verified("t", "c", "p", operator_id="op", request_id="req")
        assert False, "audit must fail"
    except OSError:
        pass
    assert recovery.calls == 1
    assert coordinator.reconcile_verified("t", "c", "p", operator_id="op", request_id="req") == "pending_requires_review"
    assert recovery.calls == 1
