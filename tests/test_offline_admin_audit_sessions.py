"""Offline admin access is provisioned, authenticated and session-bound, not a Qt flag."""
from pathlib import Path
import json
import os

import pytest

from mcm_solarcheck.services.offline_admin_credentials import (
    create_offline_admin_credentials, verify_offline_admin_credentials,
)
from mcm_solarcheck.services.offline_admin_audit_sessions import OfflineAdminAuditSessions
from mcm_solarcheck.services.report_preview_audit_admin import AuthorizedReportPreviewAudit
from mcm_solarcheck.services.report_release import record_release_decision
from mcm_solarcheck.storage.sqlite import ProjectDatabase

from test_report_release_decision import draft, progress


def prepare(tmp_path):
    db = ProjectDatabase(tmp_path / "inspection.sqlite3")
    db.initialize()
    for p in ("A", "B"):
        db.create_project(p, p)
    audit = AuthorizedReportPreviewAudit(db)
    path = tmp_path / "offline-admin-credentials.json"
    return db, path, OfflineAdminAuditSessions(path, audit)


def test_admin_fails_closed_until_explicit_provision_and_denies_wrong_password(tmp_path):
    db, path, admin = prepare(tmp_path)
    with pytest.raises(PermissionError):
        admin.login("root", "password")
    assert not path.exists()
    create_offline_admin_credentials(path, "root", "long passphrase for private audit")
    assert b"long passphrase for private audit" not in path.read_bytes()
    assert verify_offline_admin_credentials(path, "root", "long passphrase for private audit")
    assert not verify_offline_admin_credentials(path, "root", "wrong password")
    with pytest.raises(PermissionError):
        admin.login("root", "wrong password")
    token = admin.login("root", "long passphrase for private audit")
    assert token and token != "root"
    with pytest.raises(PermissionError):
        admin.inspect("root", "A")
    assert admin.inspect(token, "A") == ()
    with pytest.raises(FileExistsError):
        create_offline_admin_credentials(path, "root", "another passphrase for private audit")
    admin.logout(token)
    with pytest.raises(PermissionError):
        admin.inspect(token, "A")


def test_session_expiry_bruteforce_and_read_only_project_pagination(tmp_path):
    db, path, _ = prepare(tmp_path)
    create_offline_admin_credentials(path, "audit-admin", "extra long admin phrase")
    now = [0.0]
    admin = OfflineAdminAuditSessions(
        path, AuthorizedReportPreviewAudit(db), clock=lambda: now[0],
    )
    with db.connect() as sql:
        sql.execute("BEGIN IMMEDIATE")
        for index in range(55):
            record_release_decision(
                sql, draft(project="A", report_id=f"R-{index}"),
                progress(project="A"), approved_by="Operator",
                reached_preview_end=index % 2 == 0,
            )
        record_release_decision(
            sql, draft(project="B", report_id="B-report"),
            progress(project="B"), approved_by="Operator", reached_preview_end=True,
        )
    token = admin.login("audit-admin", "extra long admin phrase")
    results = admin.inspect(token, "A", limit=25)
    assert len(results) == 25
    assert results[0].report_id == "R-54"
    assert results[0].reached_preview_end is True
    assert len(admin.inspect(token, "A", limit=25, offset=50)) == 5
    assert all(row.project_id == "A" for row in results)
    assert len(admin.inspect(token, "B")) == 1
    for invalid in (-1, 10001, True):
        with pytest.raises(ValueError):
            admin.inspect(token, "A", offset=invalid)
    for invalid in (0, 101, True):
        with pytest.raises(ValueError):
            admin.inspect(token, "A", limit=invalid)
    now[0] = 15 * 60
    with pytest.raises(PermissionError):
        admin.inspect(token, "A")
    for _ in range(5):
        with pytest.raises(PermissionError):
            admin.login("audit-admin", "wrong")
    with pytest.raises(PermissionError):
        admin.login("audit-admin", "extra long admin phrase")
    now[0] += 61
    token2 = admin.login("audit-admin", "extra long admin phrase")
    admin.revoke_all()
    with pytest.raises(PermissionError):
        admin.inspect(token2, "A")


def test_admin_bootstrap_path_safety_and_no_plaintext(tmp_path):
    path = tmp_path / "admin.json"
    with pytest.raises(ValueError):
        create_offline_admin_credentials(Path("relative.json"), "admin", "long valid password")
    with pytest.raises(ValueError):
        create_offline_admin_credentials(path, "", "long valid password")
    with pytest.raises(ValueError):
        create_offline_admin_credentials(path, "admin", "short")
    target = tmp_path / "target.json"
    if hasattr(os, "symlink"):
        path.symlink_to(target)
        with pytest.raises(ValueError, match="symlink"):
            create_offline_admin_credentials(path, "admin", "long valid password")
        assert not verify_offline_admin_credentials(path, "admin", "long valid password")
        path.unlink()
    create_offline_admin_credentials(path, "admin", "long valid password")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert set(saved) == {"version", "actor_id", "salt", "verifier"}
    assert saved["verifier"] != "long valid password"
    if os.name == "posix":
        path.chmod(0o644)
        assert not verify_offline_admin_credentials(path, "admin", "long valid password")
    with pytest.raises(FileExistsError):
        create_offline_admin_credentials(path, "admin", "another valid password")
