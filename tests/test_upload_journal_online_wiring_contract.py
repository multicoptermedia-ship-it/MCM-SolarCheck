"""Ensure normal online construction carries durable upload journal to HTTP."""
from pathlib import Path


def test_persistence_constructs_journal():
    source = Path("src/mcm_solarcheck/infrastructure/online_persistence.py").read_text(encoding="utf-8")
    assert "upload_attempts=SQLiteUploadAttemptStore(database)" in source


def test_online_services_expose_journal():
    source = Path("src/mcm_solarcheck/services/online_composition.py").read_text(encoding="utf-8")
    assert "upload_attempts=persistence.upload_attempts" in source


def test_http_prefers_explicit_override_then_product_journal():
    source = Path("src/mcm_solarcheck/online/http_entrypoint.py").read_text(encoding="utf-8")
    assert "upload_attempt_store if upload_attempt_store is not None else getattr(product.services, 'upload_attempts', None)" in source
