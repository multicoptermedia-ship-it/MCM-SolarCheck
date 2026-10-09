"""Unchecked upload choice must not preserve earlier consent."""
from pathlib import Path


def test_upload_decline_records_withdrawal():
    source = Path("src/mcm_solarcheck/infrastructure/verification_http_server.py").read_text(encoding="utf-8")
    assert 'if consent_choice == "granted":' in source
    assert 'training_consent_service.grant(customer_id=user_id, project_id=project_id)' in source
    assert 'training_consent_service.withdraw(customer_id=user_id, project_id=project_id)' in source
    assert 'if training_consent_service is not None:' in source
