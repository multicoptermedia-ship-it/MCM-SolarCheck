"""A previously granted training permission is invalidated before file mutation."""
from pathlib import Path


def test_previous_consent_revoked_before_upload_storage():
    source = Path("src/mcm_solarcheck/infrastructure/verification_http_server.py").read_text(encoding="utf-8")
    handler = source.split("def _handle_project_upload(self) -> None:", 1)[1].split("def _handle_create_project", 1)[0]
    revoke = handler.index("training_consent_service.withdraw(customer_id=user_id, project_id=project_id)")
    store = handler.index("upload = project_upload_service.upload(")
    grant = handler.index("training_consent_service.grant(customer_id=user_id, project_id=project_id)")
    assert revoke < store < grant


def test_legacy_audit_event_constraint_remains_compatible():
    source = Path("src/mcm_solarcheck/infrastructure/sqlite_training_consent.py").read_text(encoding="utf-8")
    assert "CHECK(event IN ('granted','withdrawn'))" in source
