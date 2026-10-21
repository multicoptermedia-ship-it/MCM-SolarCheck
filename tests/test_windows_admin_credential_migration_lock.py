"""Security regression tests for explicit legacy Windows migration and lock protocol."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path

import pytest

from mcm_solarcheck.offline import admin_setup
from mcm_solarcheck.services import offline_admin_credentials as credentials
from mcm_solarcheck.services.offline_admin_credentials import (
    create_offline_admin_credentials, credential_revision,
    migrate_legacy_windows_admin_credentials, rotate_offline_admin_password,
    verify_offline_admin_credentials,
)
from test_windows_admin_dpapi_boundary import simulated_windows, PASSWORD, NEXT


def make_legacy_v1(path, monkeypatch):
    """Create a genuine old-format v1 verifier before simulating Windows."""
    with monkeypatch.context() as m:
        m.setattr(credentials, "_windows_user_protection", lambda: False)
        create_offline_admin_credentials(path, "root", PASSWORD)
    return path.read_bytes()


def test_migrate_windows_v1_requires_old_password_and_preserves_account(
    tmp_path, simulated_windows, monkeypatch,
):
    path = tmp_path / "admin.json"
    original = make_legacy_v1(path, monkeypatch)
    with pytest.raises(PermissionError):
        migrate_legacy_windows_admin_credentials(path, "root", "wrong old password")
    assert path.read_bytes() == original
    assert not verify_offline_admin_credentials(path, "root", PASSWORD)
    migrate_legacy_windows_admin_credentials(path, "root", PASSWORD)
    protected = json.loads(path.read_text())
    assert protected["version"] == 2
    assert protected["scheme"] == "dpapi-current-user-scrypt"
    assert verify_offline_admin_credentials(path, "root", PASSWORD)
    assert credential_revision(path) is not None
    assert path.read_bytes() != original
    with pytest.raises(PermissionError):
        migrate_legacy_windows_admin_credentials(path, "root", PASSWORD)
    with pytest.raises(FileExistsError):
        create_offline_admin_credentials(path, "root", PASSWORD)
    assert not list(tmp_path.glob(".offline-admin-rotate-*"))


def test_migration_cli_demands_explicit_flag_and_hidden_password(
    tmp_path, simulated_windows, monkeypatch, capsys,
):
    database = tmp_path / "inspection.sqlite"
    path = credentials.default_admin_credential_path(database)
    before = make_legacy_v1(path, monkeypatch)
    monkeypatch.setattr("builtins.input", lambda *_: "root")
    monkeypatch.setattr(admin_setup, "getpass", lambda *_: "incorrect")
    with pytest.raises(PermissionError):
        admin_setup.main(["--database", str(database), "--migrate-legacy-windows"])
    assert path.read_bytes() == before
    monkeypatch.setattr(admin_setup, "getpass", lambda *_: PASSWORD)
    assert admin_setup.main(["--database", str(database), "--migrate-legacy-windows"]) == 0
    assert verify_offline_admin_credentials(path, "root", PASSWORD)
    stdout = capsys.readouterr().out
    assert PASSWORD not in stdout
    assert "gebunden" in stdout


def test_existing_protected_windows_credentials_never_migrate_again(
    tmp_path, simulated_windows,
):
    path = tmp_path / "admin.json"
    create_offline_admin_credentials(path, "root", PASSWORD)
    before = path.read_bytes()
    with pytest.raises(PermissionError):
        migrate_legacy_windows_admin_credentials(path, "root", PASSWORD)
    assert path.read_bytes() == before


def test_posix_is_not_eligible_for_windows_migration(tmp_path):
    import sys
    if sys.platform == "win32":
        pytest.skip("native Windows path is checked separately")
    path = tmp_path / "admin.json"
    create_offline_admin_credentials(path, "root", PASSWORD)
    with pytest.raises(OSError, match="Windows"):
        migrate_legacy_windows_admin_credentials(path, "root", PASSWORD)


def test_cooperating_threads_cannot_both_rotate_using_same_old_password(tmp_path):
    path = tmp_path / "admin.json"
    create_offline_admin_credentials(path, "root", PASSWORD)
    outcomes = []
    choices = (NEXT, "yet another wholly distinct admin password")

    def attempt(new_password):
        try:
            rotate_offline_admin_password(path, "root", PASSWORD, new_password)
            return "changed"
        except PermissionError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, choices))
    assert sorted(outcomes) == ["changed", "rejected"]
    assert not verify_offline_admin_credentials(path, "root", PASSWORD)
    assert sum(verify_offline_admin_credentials(path, "root", candidate)
               for candidate in choices) == 1
    assert path.with_name(path.name + ".lock").exists()
    assert not list(tmp_path.glob(".offline-admin-rotate-*"))


def test_existing_symlink_lock_is_rejected_before_new_admin_file(
    tmp_path,
):
    if os.name != "posix":
        pytest.skip("POSIX O_NOFOLLOW symlink case")
    path = tmp_path / "admin.json"
    linked = path.with_name(path.name + ".lock")
    linked.symlink_to(tmp_path / "not-present-target")
    with pytest.raises((OSError, PermissionError)):
        create_offline_admin_credentials(path, "root", PASSWORD)
    assert not path.exists()
    assert linked.is_symlink()


def test_unsafe_posix_lock_permissions_deny_rotation(tmp_path):
    if os.name != "posix":
        pytest.skip("POSIX owner-only lock contract")
    path = tmp_path / "admin.json"
    create_offline_admin_credentials(path, "root", PASSWORD)
    locked = path.with_name(path.name + ".lock")
    locked.chmod(0o644)
    before = path.read_bytes()
    with pytest.raises(PermissionError):
        rotate_offline_admin_password(path, "root", PASSWORD, NEXT)
    assert path.read_bytes() == before
