"""Consent gate must fail closed after withdrawal or without permission."""
import pytest

from mcm_solarcheck.services.training_consent import TrainingConsentService


class MemoryStore:
    def __init__(self):
        self.events = {}

    def record(self, *, customer_id, project_id, event, notice_version):
        self.events[(customer_id, project_id)] = event

    def is_granted(self, *, customer_id, project_id):
        return self.events.get((customer_id, project_id)) == "granted"


def test_training_requires_current_consent():
    store = MemoryStore()
    service = TrainingConsentService(store, lambda user, project: user == "owner" and project == "p")
    with pytest.raises(PermissionError):
        service.require_granted(customer_id="owner", project_id="p")
    service.grant(customer_id="owner", project_id="p")
    service.require_granted(customer_id="owner", project_id="p")
    service.withdraw(customer_id="owner", project_id="p")
    with pytest.raises(PermissionError):
        service.require_granted(customer_id="owner", project_id="p")


def test_other_customers_cannot_use_project_consent():
    service = TrainingConsentService(MemoryStore(), lambda user, project: user == "owner")
    service.grant(customer_id="owner", project_id="p")
    with pytest.raises(PermissionError):
        service.require_granted(customer_id="intruder", project_id="p")
