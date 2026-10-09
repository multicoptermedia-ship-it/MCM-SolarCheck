"""Upload UI must match the existing authenticated HTTP adapter."""
from pathlib import Path
import mcm_solarcheck.infrastructure.verification_http_server as http_adapter


def test_existing_upload_contract_remains_authoritative():
    source = Path(http_adapter.__file__).read_text(encoding="utf-8")
    assert 'parsed.path == "/project-upload"' in source
    assert 'self._require_customer_user()' in source
    assert 'customer_entry(user_id)' in source
    assert 'self.headers.get("X-SolarCheck-Project-Id"' in source
    assert 'self.headers.get("X-SolarCheck-Filename"' in source
    assert "MAX_PROJECT_UPLOAD_BYTES = 250 * 1024 * 1024" in source
