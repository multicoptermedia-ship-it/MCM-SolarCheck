"""Guardrails for revocation and permission checks."""
from pathlib import Path

import pytest

from mcm_solarcheck.services.training_consent import TrainingConsentService


class Store:
    def __init__(self):
        self.granted = False

    def record(self, **kwargs):
        self.granted = kwargs["event"] == "granted"

    def is_granted(self, **kwargs):
        return self.granted


def test_withdrawal_revokes_permission():
    store = Store()
    service = TrainingConsentService(store, lambda customer, project: customer == "owner")
    service.grant(customer_id="owner", project_id="p")
    assert service.is_granted(customer_id="owner", project_id="p")
    service.withdraw(customer_id="owner", project_id="p")
    assert not service.is_granted(customer_id="owner", project_id="p")
    with pytest.raises(PermissionError):
        service.is_granted(customer_id="other", project_id="p")


def test_withdrawal_requires_authenticated_customer_and_project():
    server = Path("src/mcm_solarcheck/infrastructure/verification_http_server.py").read_text(encoding="utf-8")
    assert 'parsed.path == "/api/training-consent-withdraw"' in server
    assert 'training_consent_service.withdraw(customer_id=user_id, project_id=project_id)' in server
    assert "self._require_customer_user()" in server


def test_frontend_offers_withdrawal():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert 'id="consent-withdraw-button"' in html
    assert "fetch('/api/training-consent-withdraw'" in html
