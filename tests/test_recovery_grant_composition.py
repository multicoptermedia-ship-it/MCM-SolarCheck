from mcm_solarcheck.services.authorized_grant_administration import GrantAdministrator
from mcm_solarcheck.services.recovery_authorization import RecoveryOperator
from mcm_solarcheck.services.recovery_grant_composition import (
    build_grant_administration, build_project_recovery,
)


class Coordinator:
    def __init__(self):
        self.calls = 0

    def reconcile_verified(self, *args, **kwargs):
        self.calls += 1
        return "journal_reconciled"


def test_composed_grant_write_controls_read_only_recovery(tmp_path):
    database = tmp_path / "shared.db"
    admin = build_grant_administration(database)
    coordinator = Coordinator()
    recovery = build_project_recovery(coordinator, database)
    operator = RecoveryOperator("op", True, frozenset({"publication:reconcile"}))
    administrator = GrantAdministrator("admin", True, frozenset({"publication:manage_grants"}))

    def attempt():
        return recovery.reconcile_verified("t", "c", "p", identity=operator, request_id="req")

    assert attempt() == "permission_denied"
    assert admin.set_grant(administrator, "op", "c", "p", True) == "grant_updated"
    assert attempt() == "journal_reconciled"
    assert admin.set_grant(administrator, "op", "c", "p", False) == "grant_updated"
    assert attempt() == "permission_denied"
    assert coordinator.calls == 1


def test_read_only_grants_do_not_expose_set_grant(tmp_path):
    coordinator = Coordinator()
    recovery = build_project_recovery(coordinator, tmp_path / "shared.db")
    assert not hasattr(recovery.grants, "set_grant")
