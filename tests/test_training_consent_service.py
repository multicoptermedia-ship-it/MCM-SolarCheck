"""No cross-customer permission mutations."""
import pytest

from mcm_solarcheck.services.training_consent import TrainingConsentService


class Projects:
    def get_project_for_customer(self, customer_id, project_id):
        if (customer_id, project_id) != ("alice", "project"):
            raise PermissionError("not owner")


class Store:
    def __init__(self):
        self.calls = []

    def record(self, **kwargs):
        self.calls.append(kwargs)


def test_owner_can_grant_and_withdraw():
    store = Store()
    service = TrainingConsentService(store, Projects())
    service.grant(customer_id="alice", project_id="project")
    service.withdraw(customer_id="alice", project_id="project")
    assert [call["event"] for call in store.calls] == ["granted", "withdrawn"]


def test_other_customer_cannot_change_permission():
    store = Store()
    with pytest.raises(PermissionError):
        TrainingConsentService(store, Projects()).grant(customer_id="bob", project_id="project")
    assert store.calls == []
