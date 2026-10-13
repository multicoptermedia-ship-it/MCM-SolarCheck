from mcm_solarcheck.infrastructure.sqlite_audited_recovery_grants import SQLiteAuditedRecoveryGrants
from mcm_solarcheck.services.authorized_grant_administration import (
    AuthorizedGrantAdministration, GrantAdministrator,
)


def test_grant_and_audit_are_committed_together(tmp_path):
    grants = SQLiteAuditedRecoveryGrants(tmp_path / "grants.db")
    admin = AuthorizedGrantAdministration(grants)
    identity = GrantAdministrator("admin", True, frozenset({"publication:manage_grants"}))
    assert admin.set_grant(identity, "op", "c", "p", True) == "grant_updated"
    assert grants.allowed("op", "c", "p")
    assert admin.set_grant(identity, "op", "c", "p", False) == "grant_updated"
    assert not grants.allowed("op", "c", "p")
    events = grants.list_events("op", "c", "p")
    assert [(e[1], e[2], e[3]) for e in events] == [
        ("admin", None, 1), ("admin", 1, 0)
    ]


def test_denied_admin_does_not_write_grant_or_audit(tmp_path):
    grants = SQLiteAuditedRecoveryGrants(tmp_path / "grants.db")
    admin = AuthorizedGrantAdministration(grants)
    denied = [
        None,
        GrantAdministrator("admin", False, frozenset({"publication:manage_grants"})),
        GrantAdministrator("admin", True, frozenset({"publication:reconcile"})),
        GrantAdministrator("", True, frozenset({"publication:manage_grants"})),
    ]
    for identity in denied:
        assert admin.set_grant(identity, "op", "c", "p", True) == "permission_denied"
    assert not grants.allowed("op", "c", "p")
    assert grants.list_events("op", "c", "p") == []
