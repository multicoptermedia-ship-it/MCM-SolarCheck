"""Consent request origin hardening contract."""
from pathlib import Path


def test_withdrawal_requires_matching_origin():
    source = Path("src/mcm_solarcheck/infrastructure/verification_http_server.py").read_text(encoding="utf-8")
    assert 'if not self._same_origin_request():' in source
    assert 'cross-origin consent withdrawal is forbidden' in source
    assert 'parsed_origin.netloc == expected_host' in source


def test_upload_rejects_explicit_foreign_origin():
    source = Path("src/mcm_solarcheck/infrastructure/verification_http_server.py").read_text(encoding="utf-8")
    assert 'if self.headers.get("Origin") and not self._same_origin_request():' in source
    assert 'cross-origin project upload is forbidden' in source
