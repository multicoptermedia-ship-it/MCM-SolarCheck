"""Explicit offline administrator rotation: no default, no overwrite, no stale sessions."""
from __future__ import annotations

import json
import os

import pytest

from mcm_solarcheck.services.offline_admin_credentials import (
    create_offline_admin_credentials, credential_revision,
    rotate_offline_admin_password, verify_offline_admin_credentials,
)
from mcm_solarcheck.services.offline_admin_audit_sessions import OfflineAdminAuditSessions
from mcm_solarcheck.services.report_preview_audit_admin import AuthorizedReportPreviewAudit
from mcm_solarcheck.storage.sqlite import ProjectDatabase


OLD = "correct old administrator secret"
NEW = "completely different new admin secret"


def configured(tmp_path):
    db = ProjectDatabase(tmp_path / "inspections.sqlite3")
    db.initialize()
    db.create_project("P1", "Project 1")
    path = tmp_path / "offline-admin-credentials.json"
    create_offline_admin_credentials(path, "owner", OLD)
    return db, path


def test_reauthentication_rotates_scrypt_credentials_and_revokes_all_tokens(tmp_path):
    db, path = configured(tmp_path)
    controller = OfflineAdminAuditSessions(path, AuthorizedReportPreviewAudit(db))
    other_window = OfflineAdminAuditSessions(path, AuthorizedReportPreviewAudit(db))
    first = controller.login("owner", OLD)
    second = controller.login("owner", OLD)
    external = other_window.login("owner", OLD)
    revision = credential_revision(path)
    controller.change_password(first, OLD, NEW)
    assert credential_revision(path) != revision
    assert not verify_offline_admin_credentials(path, "owner", OLD)
    assert verify_offline_admin_credentials(path, "owner", NEW)
    assert OLD.encode() not in path.read_bytes()
    assert NEW.encode() not in path.read_bytes()
    for token in (first, second):
        with pytest.raises(PermissionError):
            controller.inspect(token, "P1")
    with pytest.raises(PermissionError, match="invalidated"):
        other_window.inspect(external, "P1")
    with pytest.raises(PermissionError):
        controller.login("owner", OLD)
    current = controller.login("owner", NEW)
    assert controller.inspect(current, "P1") == ()
    assert json.loads(path.read_text())["actor_id"] == "owner"
    if os.name == "posix":
        assert path.stat().st_mode & 0o077 == 0
    assert list(tmp_path.glob(".offline-admin-rotate-*")) == []


def test_wrong_password_never_changes_credential_and_kills_failed_session(tmp_path):
    db, path = configured(tmp_path)
    controller = OfflineAdminAuditSessions(path, AuthorizedReportPreviewAudit(db))
    token = controller.login("owner", OLD)
    original = path.read_bytes()
    with pytest.raises(PermissionError):
        controller.change_password(token, "not-the-current-pass", NEW)
    assert path.read_bytes() == original
    with pytest.raises(PermissionError):
        controller.inspect(token, "P1")
    assert verify_offline_admin_credentials(path, "owner", OLD)


@pytest.mark.parametrize("proposed", ["short", "same", "", 42, None])
def test_new_password_validation_is_fail_closed(tmp_path, proposed):
    db, path = configured(tmp_path)
    controller = OfflineAdminAuditSessions(path, AuthorizedReportPreviewAudit(db))
    token = controller.login("owner", OLD)
    before = path.read_bytes()
    if proposed == "same":
        proposed = OLD
    with pytest.raises((TypeError, ValueError)):
        controller.change_password(token, OLD, proposed)
    assert path.read_bytes() == before
    assert controller.inspect(token, "P1") == ()


def test_rotation_failure_keeps_old_credentials_and_cleans_staging(
    tmp_path, monkeypatch,
):
    from mcm_solarcheck.services import offline_admin_credentials as module
    db, path = configured(tmp_path)
    controller = OfflineAdminAuditSessions(path, AuthorizedReportPreviewAudit(db))
    token = controller.login("owner", OLD)
    original = path.read_bytes()
    def reject_replace(*_args):
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(module.os, "replace", reject_replace)
    with pytest.raises(OSError):
        controller.change_password(token, OLD, NEW)
    assert path.read_bytes() == original
    assert verify_offline_admin_credentials(path, "owner", OLD)
    assert not verify_offline_admin_credentials(path, "owner", NEW)
    assert not list(tmp_path.glob(".offline-admin-rotate-*"))


def test_external_rotation_or_bad_permissions_invalidates_live_session(tmp_path):
    db, path = configured(tmp_path)
    controller = OfflineAdminAuditSessions(path, AuthorizedReportPreviewAudit(db))
    token = controller.login("owner", OLD)
    rotate_offline_admin_password(path, "owner", OLD, NEW)
    with pytest.raises(PermissionError, match="invalidated"):
        controller.inspect(token, "P1")
    token2 = controller.login("owner", NEW)
    if os.name == "posix":
        path.chmod(0o644)
        with pytest.raises(PermissionError, match="invalidated"):
            controller.inspect(token2, "P1")
        with pytest.raises(PermissionError):
            controller.login("owner", NEW)


def test_unprovisioned_symlink_or_corrupt_file_cannot_rotate(tmp_path):
    db = ProjectDatabase(tmp_path / "empty.sqlite3")
    db.initialize()
    absent = tmp_path / "admin-absent.json"
    with pytest.raises(PermissionError):
        rotate_offline_admin_password(absent, "owner", OLD, NEW)
    target = tmp_path / "real.json"
    create_offline_admin_credentials(target, "owner", OLD)
    alias = tmp_path / "alias.json"
    if hasattr(os, "symlink"):
        alias.symlink_to(target)
        with pytest.raises(PermissionError):
            rotate_offline_admin_password(alias, "owner", OLD, NEW)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{bad-json", encoding="utf-8")
    if os.name == "posix":
        invalid.chmod(0o600)
    with pytest.raises(PermissionError):
        rotate_offline_admin_password(invalid, "owner", OLD, NEW)
