"""Synthetic Windows DPAPI boundary checks, runnable on Linux CI.

Actual Windows Crypt32 and ACL behavior still requires a native Windows runner.
"""
from __future__ import annotations

import base64
import json
import os

import pytest

from mcm_solarcheck.services import offline_admin_credentials as credentials
from mcm_solarcheck.services import windows_dpapi
from mcm_solarcheck.services.offline_admin_audit_sessions import OfflineAdminAuditSessions
from mcm_solarcheck.services.report_preview_audit_admin import AuthorizedReportPreviewAudit
from mcm_solarcheck.storage.sqlite import ProjectDatabase


PASSWORD = "correctly lengthy admin passphrase"
NEXT = "different correctly lengthy password"


@pytest.fixture
def simulated_windows(monkeypatch):
    identity = ["Windows-user-1"]
    monkeypatch.setattr(credentials, "_windows_user_protection", lambda: True)

    def protect(raw):
        tag = identity[0].encode("ascii")
        return b"FAKE_DPAPI:" + tag + b":" + bytes(v ^ 91 for v in raw)

    def unprotect(cipher):
        prefix = b"FAKE_DPAPI:" + identity[0].encode("ascii") + b":"
        if not cipher.startswith(prefix):
            raise OSError("wrong Windows user")
        return bytes(v ^ 91 for v in cipher[len(prefix):])

    monkeypatch.setattr(windows_dpapi, "protect_for_current_user", protect)
    monkeypatch.setattr(windows_dpapi, "unprotect_for_current_user", unprotect)
    return identity


def test_windows_creates_v2_sealed_scrypt_record_and_no_raw_hash(
    tmp_path, simulated_windows,
):
    path = tmp_path / "admin.json"
    credentials.create_offline_admin_credentials(path, "root", PASSWORD)
    raw = path.read_bytes()
    body = json.loads(raw)
    assert set(body) == {"version", "scheme", "sealed"}
    assert body["version"] == 2
    assert body["scheme"] == "dpapi-current-user-scrypt"
    assert "verifier" not in raw.decode("utf-8")
    assert PASSWORD.encode("utf-8") not in raw
    assert credentials.verify_offline_admin_credentials(path, "root", PASSWORD)
    assert not credentials.verify_offline_admin_credentials(path, "root", "wrong")
    current = credentials.credential_revision(path)
    assert current is not None
    simulated_windows[0] = "Windows-user-2"
    assert credentials.credential_revision(path) is None
    assert not credentials.verify_offline_admin_credentials(path, "root", PASSWORD)
    simulated_windows[0] = "Windows-user-1"
    assert credentials.credential_revision(path) == current


def test_window_bound_rotation_reauthenticates_and_invalidates_sessions(
    tmp_path, simulated_windows,
):
    db = ProjectDatabase(tmp_path / "inspection.sqlite")
    db.initialize()
    db.create_project("P1", "Project 1")
    path = tmp_path / "admin.json"
    credentials.create_offline_admin_credentials(path, "operator", PASSWORD)
    sessions = OfflineAdminAuditSessions(path, AuthorizedReportPreviewAudit(db))
    token = sessions.login("operator", PASSWORD)
    old_bytes = path.read_bytes()
    sessions.change_password(token, PASSWORD, NEXT)
    assert path.read_bytes() != old_bytes
    assert not credentials.verify_offline_admin_credentials(path, "operator", PASSWORD)
    assert credentials.verify_offline_admin_credentials(path, "operator", NEXT)
    with pytest.raises(PermissionError):
        sessions.inspect(token, "P1")
    new_token = sessions.login("operator", NEXT)
    assert sessions.inspect(new_token, "P1") == ()


def test_windows_legacy_v1_is_rejected_until_explicit_migration(
    tmp_path, simulated_windows,
):
    path = tmp_path / "admin.json"
    salt = b"0" * 32
    import hashlib
    verifier = hashlib.scrypt(
        PASSWORD.encode(), salt=salt, n=1 << 14, r=8, p=1, dklen=32,
    )
    old = {
        "version": 1, "actor_id": "root",
        "salt": salt.hex(), "verifier": verifier.hex(),
    }
    path.write_text(json.dumps(old), encoding="utf-8")
    if os.name == "posix":
        path.chmod(0o600)
    before = path.read_bytes()
    assert not credentials.verify_offline_admin_credentials(path, "root", PASSWORD)
    assert credentials.credential_revision(path) is None
    with pytest.raises(PermissionError):
        credentials.rotate_offline_admin_password(path, "root", PASSWORD, NEXT)
    assert path.read_bytes() == before
    with pytest.raises(FileExistsError):
        credentials.create_offline_admin_credentials(path, "root", PASSWORD)


def test_corrupt_windows_record_fails_closed_without_plaintext_fallback(
    tmp_path, simulated_windows,
):
    path = tmp_path / "admin.json"
    credentials.create_offline_admin_credentials(path, "root", PASSWORD)
    record = json.loads(path.read_text())
    record["sealed"] = base64.b64encode(b"not-DPAPI").decode()
    path.write_text(json.dumps(record))
    if os.name == "posix":
        path.chmod(0o600)
    assert not credentials.verify_offline_admin_credentials(path, "root", PASSWORD)
    assert credentials.credential_revision(path) is None


def test_real_dpapi_functions_cannot_be_used_on_non_windows():
    import sys
    if sys.platform == "win32":
        pytest.skip("native Windows DPAPI testing belongs on Windows")
    with pytest.raises(OSError, match="unavailable"):
        windows_dpapi.protect_for_current_user(b"test")
    with pytest.raises(OSError, match="unavailable"):
        windows_dpapi.unprotect_for_current_user(b"test")
