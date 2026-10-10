from mcm_solarcheck.infrastructure.sqlite_recovery_attempts import SQLiteRecoveryAttempts
from mcm_solarcheck.services.idempotent_audited_recovery import IdempotentAuditedRecovery


class Recovery:
    def __init__(self):
        self.calls = 0

    def reconcile_verified(self, *args, **kwargs):
        self.calls += 1
        return "journal_reconciled"


def test_replay_returns_stored_result_without_reexecution(tmp_path):
    attempts = SQLiteRecoveryAttempts(tmp_path / "attempts.db")
    recovery = Recovery()
    wrapper = IdempotentAuditedRecovery(recovery, attempts)
    args = ("t", "c", "p")
    assert wrapper.reconcile_verified(*args, operator_id="op", request_id="req") == "journal_reconciled"
    assert wrapper.reconcile_verified(*args, operator_id="op", request_id="req") == "journal_reconciled"
    assert recovery.calls == 1
    assert wrapper.reconcile_verified(*args, operator_id="other", request_id="req") == "request_identity_conflict"


def test_ambiguous_pending_request_is_not_replayed(tmp_path):
    attempts = SQLiteRecoveryAttempts(tmp_path / "attempts.db")
    assert attempts.claim("req", "t", "c", "p", "op") == ("new", None)
    recovery = Recovery()
    wrapper = IdempotentAuditedRecovery(recovery, attempts)
    assert wrapper.reconcile_verified("t", "c", "p", operator_id="op", request_id="req") == "pending_requires_review"
    assert recovery.calls == 0


def test_failed_recovery_keeps_pending_for_review(tmp_path):
    class FailingRecovery:
        def reconcile_verified(self, *args, **kwargs):
            raise OSError("audit unavailable")

    attempts = SQLiteRecoveryAttempts(tmp_path / "attempts.db")
    wrapper = IdempotentAuditedRecovery(FailingRecovery(), attempts)
    try:
        wrapper.reconcile_verified("t", "c", "p", operator_id="op", request_id="req")
        assert False, "expected audit failure"
    except OSError:
        pass
    assert attempts.inspect("req", "t", "c", "p", "op") == ("pending", None)
