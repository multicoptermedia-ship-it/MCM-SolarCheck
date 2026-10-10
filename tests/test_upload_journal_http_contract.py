"""Optional upload journal integration contract."""
from pathlib import Path


def test_http_records_attempt_before_storage():
    source = Path("src/mcm_solarcheck/infrastructure/verification_http_server.py").read_text(encoding="utf-8")
    section = source.split("def _handle_project_upload(self) -> None:", 1)[1].split("def _handle_create_project", 1)[0]
    assert section.index("upload_attempt_store.begin(") < section.index("project_upload_service.upload(")
    assert "upload_attempt_store.finish(attempt_id, succeeded=True)" in section
    assert "upload_attempt_store.finish(attempt_id, succeeded=False)" in section


def test_online_entrypoint_accepts_upload_journal():
    source = Path("src/mcm_solarcheck/online/http_entrypoint.py").read_text(encoding="utf-8")
    assert "upload_attempt_store=(" in source
    assert "getattr(product.services, 'upload_attempts', None)" in source
