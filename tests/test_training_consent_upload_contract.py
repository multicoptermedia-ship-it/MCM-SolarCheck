"""Guardrails for the optional consent upload contract."""
from pathlib import Path


def test_upload_checkbox_is_opt_in_and_sends_choice():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert 'id="training-consent" type="checkbox"' in html
    assert 'id="training-consent" type="checkbox" checked' not in html
    assert "'X-SolarCheck-Training-Consent':document.getElementById('training-consent').checked?'granted':'declined'" in html


def test_server_rejects_grant_without_audit_service():
    server = Path("src/mcm_solarcheck/infrastructure/verification_http_server.py").read_text(encoding="utf-8")
    assert 'if consent_choice == "granted" and training_consent_service is None:' in server
    assert 'training_consent_service.grant(customer_id=user_id, project_id=project_id)' in server
    assert 'if consent_choice not in ("granted", "declined"):' in server
