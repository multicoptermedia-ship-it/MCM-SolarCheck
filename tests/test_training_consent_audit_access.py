"""Consent audit history must be scoped to the project owner."""
import pytest
from mcm_solarcheck.services.training_consent import TrainingConsentService


class Store:
    def __init__(self):
        self.calls = []

    def events(self, **kwargs):
        self.calls.append(kwargs)
        return [("withdrawn", "training-images-v1", "2026-10-09T00:00:00+00:00")]


def test_owner_can_read_audit():
    store = Store()
    service = TrainingConsentService(store, lambda customer, project: (customer, project) == ("a", "p"))
    assert service.audit_events(customer_id="a", project_id="p")[0][0] == "withdrawn"
    assert store.calls == [{"customer_id": "a", "project_id": "p"}]


def test_other_customer_cannot_read_audit():
    store = Store()
    service = TrainingConsentService(store, lambda customer, project: (customer, project) == ("a", "p"))
    with pytest.raises(PermissionError):
        service.audit_events(customer_id="b", project_id="p")
    assert store.calls == []
