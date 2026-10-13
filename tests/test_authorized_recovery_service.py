from mcm_solarcheck.services.authorized_recovery_service import AuthorizedRecoveryService
from mcm_solarcheck.services.recovery_authorization import RecoveryAuthorization, RecoveryOperator


class Coordinator:
    def __init__(self):
        self.calls = []

    def reconcile_verified(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return "journal_reconciled"


def test_authorized_operator_reaches_coordinator():
    coordinator = Coordinator()
    service = AuthorizedRecoveryService(coordinator)
    identity = RecoveryOperator("op-1", True, frozenset({"publication:reconcile"}))
    assert service.reconcile_verified("t", "c", "p", identity=identity, request_id="req") == "journal_reconciled"
    assert coordinator.calls == [(("t", "c", "p"), {"operator_id": "op-1", "request_id": "req"})]


def test_denied_identities_never_reach_coordinator():
    coordinator = Coordinator()
    service = AuthorizedRecoveryService(coordinator)
    denied = [
        None,
        {"operator_id": "op", "authenticated": True, "permissions": {"publication:reconcile"}},
        RecoveryOperator("op", False, frozenset({"publication:reconcile"})),
        RecoveryOperator("op", True, frozenset()),
        RecoveryOperator("", True, frozenset({"publication:reconcile"})),
        RecoveryOperator("op", True, {"publication:reconcile"}),
    ]
    for identity in denied:
        assert service.reconcile_verified("t", "c", "p", identity=identity, request_id="req") == "permission_denied"
    assert coordinator.calls == []


def test_policy_requires_exact_permission():
    policy = RecoveryAuthorization()
    assert policy.authorize(RecoveryOperator("op", True, frozenset({"publication:read"}))) is None
