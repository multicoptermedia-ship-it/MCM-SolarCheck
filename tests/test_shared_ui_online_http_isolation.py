"""A different customer must never see another customer's project."""
from types import SimpleNamespace
from shared_ui.online_access import authorized_online_projects


class Store:
    def projects_for_customer(self, customer_id):
        return (SimpleNamespace(project_id="alice-only", name="A"),) if customer_id == "alice" else ()


def test_customer_isolation():
    assert authorized_online_projects("bob", customer_entry=lambda _: None, project_service=Store()) == []
    assert authorized_online_projects("alice", customer_entry=lambda _: None, project_service=Store()) == [{"id": "alice-only", "name": "A"}]
