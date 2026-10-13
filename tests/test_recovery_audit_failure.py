import pytest

from mcm_solarcheck.services.audited_publication_recovery import AuditedPublicationRecovery


class Recovery:
    def __init__(self):
        self.calls = 0

    def reconcile_verified(self, *args):
        self.calls += 1
        return "journal_reconciled"


class Audit:
    def __init__(self, fail_at):
        self.calls = 0
        self.fail_at = fail_at
        self.events = []

    def record(self, *args):
        self.calls += 1
        if self.calls == self.fail_at:
            raise OSError("audit unavailable")
        self.events.append(args[-1])


def test_failed_intent_audit_prevents_recovery():
    recovery = Recovery()
    wrapper = AuditedPublicationRecovery(recovery, Audit(1))
    with pytest.raises(OSError, match="audit unavailable"):
        wrapper.reconcile_verified("t", "c", "p", operator_id="operator")
    assert recovery.calls == 0


def test_failed_outcome_audit_is_not_reported_as_success():
    recovery = Recovery()
    audit = Audit(2)
    wrapper = AuditedPublicationRecovery(recovery, audit)
    with pytest.raises(OSError, match="audit unavailable"):
        wrapper.reconcile_verified("t", "c", "p", operator_id="operator")
    assert recovery.calls == 1
    assert audit.events == ["requested"]
