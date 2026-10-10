"""Customer entry gate runs before any project query."""
from types import SimpleNamespace
import pytest

from shared_ui.online_access import authorized_online_projects


def test_entry_gate_blocks_project_reads():
    class Store:
        def projects_for_customer(self, customer_id):
            raise AssertionError("must not read after denial")

    def deny(customer_id):
        raise PermissionError("not verified")

    with pytest.raises(PermissionError):
        authorized_online_projects("alice", customer_entry=deny, project_service=Store())


def test_entry_gate_allows_scoped_read():
    class Store:
        def projects_for_customer(self, customer_id):
            assert customer_id == "alice"
            return (SimpleNamespace(project_id="a", name="West"),)

    assert authorized_online_projects("alice", customer_entry=lambda _: None, project_service=Store()) == [{"id": "a", "name": "West"}]
