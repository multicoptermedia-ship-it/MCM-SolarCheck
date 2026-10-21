"""Native Windows host checks: never substitute Linux DPAPI simulations.

GitHub windows-2022 is Windows Server, not a Windows 10 device. Run this test
on the actual Windows 10 target as part of release acceptance.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from mcm_solarcheck.services.windows_dpapi import (
    protect_for_current_user, unprotect_for_current_user,
)
from mcm_solarcheck.services.offline_admin_credentials import (
    create_offline_admin_credentials, credential_revision,
    rotate_offline_admin_password, verify_offline_admin_credentials,
    migrate_legacy_windows_admin_credentials,
)


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="native Win32 only")

PASSWORD = "Windows 10 local administrator phrase"
NEXT_PASSWORD = "Windows 10 rotated administrator phrase"


def test_native_win32_dpapi_roundtrip_and_invalid_payload():
    value = b"non-sensitive native windows dpapi regression test"
    sealed = protect_for_current_user(value)
    assert sealed != value
    assert unprotect_for_current_user(sealed) == value
    with pytest.raises(OSError):
        unprotect_for_current_user(b"not-a-valid-windows-dpapi-blob")


def test_native_win32_credentials_create_and_rotate(tmp_path):
    path = tmp_path / "admin-credentials.json"
    create_offline_admin_credentials(path, "administrator", PASSWORD)
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    assert set(wrapper) == {"version", "scheme", "sealed"}
    assert wrapper["version"] == 2
    assert PASSWORD not in path.read_text(encoding="utf-8")
    assert "verifier" not in wrapper
    assert verify_offline_admin_credentials(path, "administrator", PASSWORD)
    revision = credential_revision(path)
    assert revision is not None
    rotate_offline_admin_password(path, "administrator", PASSWORD, NEXT_PASSWORD)
    assert credential_revision(path) != revision
    assert not verify_offline_admin_credentials(path, "administrator", PASSWORD)
    assert verify_offline_admin_credentials(path, "administrator", NEXT_PASSWORD)
    with pytest.raises(PermissionError):
        migrate_legacy_windows_admin_credentials(path, "administrator", NEXT_PASSWORD)


def test_native_win32_other_process_same_account_can_read_dpapi(tmp_path):
    path = tmp_path / "admin-credentials.json"
    create_offline_admin_credentials(path, "administrator", PASSWORD)
    program = (
        "from mcm_solarcheck.services.offline_admin_credentials import "
        "verify_offline_admin_credentials as verify; "
        "from pathlib import Path; import sys; "
        "sys.exit(0 if verify(Path(sys.argv[1]),sys.argv[2],sys.argv[3]) else 10)"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    child = subprocess.run(
        [sys.executable, "-c", program, str(path), "administrator", PASSWORD],
        env=env, capture_output=True, timeout=20, check=False,
    )
    assert child.returncode == 0
    assert not child.stdout and not child.stderr
