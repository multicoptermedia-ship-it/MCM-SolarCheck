from mcm_solarcheck.infrastructure.sqlite_recovery_grants import SQLiteRecoveryGrants
from mcm_solarcheck.services.project_authorized_recovery_service import ProjectAuthorizedRecoveryService
from mcm_solarcheck.services.recovery_authorization import RecoveryOperator


class Coordinator:
    def __init__(self):
        self.calls = 0

    def reconcile_verified(self, *args, **kwargs):
        self.calls += 1
        return "journal_reconciled"


def test_project_grants_default_deny_and_can_be_revoked(tmp_path):
    grants = SQLiteRecoveryGrants(tmp_path / "grants.db")
    coordinator = Coordinator()
    service = ProjectAuthorizedRecoveryService(coordinator, grants)
    identity = RecoveryOperator("op", True, frozenset({"publication:reconcile"}))
    def run(project):
        return service.reconcile_verified("t", "c", project, identity=identity, request_id="req")
    assert run("p") == "permission_denied"
    grants.set_grant("op", "c", "p", True)
    assert run("p") == "journal_reconciled"
    assert run("other") == "permission_denied"
    grants.set_grant("op", "c", "p", False)
    assert run("p") == "permission_denied"
    assert coordinator.calls == 1


def test_untrusted_identity_cannot_use_project_grant(tmp_path):
    grants = SQLiteRecoveryGrants(tmp_path / "grants.db")
    grants.set_grant("op", "c", "p", True)
    coordinator = Coordinator()
    service = ProjectAuthorizedRecoveryService(coordinator, grants)
    identity = RecoveryOperator("op", False, frozenset({"publication:reconcile"}))
    assert service.reconcile_verified("t", "c", "p", identity=identity, request_id="req") == "permission_denied"
    assert coordinator.calls == 0
