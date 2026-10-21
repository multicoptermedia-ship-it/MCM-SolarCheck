"""Headless Qt security regression tests for local administrator-only audit view."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QTableWidget

from mcm_solarcheck.gui.offline_admin_audit_dialog import OfflineAdminAuditDialog
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.offline_admin_credentials import (
    create_offline_admin_credentials, default_admin_credential_path,
)
from mcm_solarcheck.services.offline_admin_audit_sessions import OfflineAdminAuditSessions
from mcm_solarcheck.services.report_preview_audit_admin import AuthorizedReportPreviewAudit


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def setup_window(tmp_path):
    dbpath = tmp_path / "inspections.sqlite3"
    window = build_offline_window(dbpath)
    window._project_service.create_project("P1", "Project one")
    window._project_service.create_project("P2", "Project two")
    with window._project_service.database.connect() as db:
        for number in range(27):
            cur = db.execute(
                """INSERT INTO report_release_decisions(
                    project_id,report_id,inspection_started_utc,approved_by,
                    approved_at_utc,review_digest,unclear_count,followup_note
                ) VALUES(?,?,?,?,?,?,?,?)""",
                ("P1", f"R-{number}", "2026-10-20T10:00:00+00:00",
                 "Expertin", "2026-10-21T11:00:00+00:00", "sha256-snapshot", 0, ""),
            )
            # The first record deliberately lacks a private audit bit (legacy).
            if number:
                db.execute(
                    "INSERT INTO report_release_read_audit VALUES(?,?)",
                    (cur.lastrowid, number % 2),
                )
        db.execute(
            """INSERT INTO report_release_decisions(
                project_id,report_id,inspection_started_utc,approved_by,
                approved_at_utc,review_digest,unclear_count,followup_note
            ) VALUES(?,?,?,?,?,?,?,?)""",
            ("P2", "OTHER-PROJECT", "2026-10-20T10:00:00+00:00",
             "Andere", "2026-10-21T11:00:00+00:00", "digest", 0, ""),
        )
    window._open_project("P1")
    return window, dbpath


def test_offline_admin_menu_is_not_an_online_or_review_route(tmp_path, qt_app):
    window, _ = setup_window(tmp_path)
    online = SolarCheckMainWindow(
        DeploymentMode.ONLINE, project_service=window._project_service,
    )
    try:
        assert window.findChild(
            QAction, "open_report_admin_audit",
        ) is not None
        assert online.findChild(
            QAction, "open_report_admin_audit",
        ) is None
        assert "admin" not in [route.value for route in window._pages]
    finally:
        online.close()
        window.close()


def test_gui_denies_unprovisioned_and_wrong_login_then_shows_private_history(
    tmp_path, qt_app,
):
    window, dbpath = setup_window(tmp_path)
    dialog = OfflineAdminAuditDialog(
        window._offline_admin_sessions, "P1",
        active_project=lambda: window.current_project_id,
    )
    try:
        assert dialog.table.rowCount() == 0
        dialog.user.setText("admin")
        dialog.password.setText("never-configured")
        dialog.login_button.click()
        assert dialog.stack.currentIndex() == 0
        assert dialog.table.rowCount() == 0
        path = default_admin_credential_path(dbpath)
        create_offline_admin_credentials(path, "admin", "private passphrase for tests")
        dialog.user.setText("admin")
        dialog.password.setText("incorrect credential")
        dialog.login_button.click()
        assert dialog.stack.currentIndex() == 0
        assert dialog.table.rowCount() == 0
        dialog.user.setText("admin")
        dialog.password.setText("private passphrase for tests")
        dialog.login_button.click()
        assert dialog.stack.currentIndex() == 1
        assert dialog.table.rowCount() == 25
        assert dialog.table.item(0, 1).text() == "R-26"
        assert dialog.table.item(0, 4).text() == "Nein"
        assert all(
            "OTHER-PROJECT" not in dialog.table.item(i, 1).text()
            for i in range(dialog.table.rowCount())
        )
        assert dialog.previous.isEnabled() is False
        assert dialog.next.isEnabled() is True
        dialog.next.click()
        assert dialog.table.rowCount() == 2
        assert dialog.table.item(1, 1).text() == "R-0"
        assert dialog.table.item(1, 4).text() == "Unbekannt"
        assert dialog.next.isEnabled() is False
        assert dialog.previous.isEnabled() is True
        dialog.logout_button.click()
        assert dialog.stack.currentIndex() == 0
        assert dialog.table.rowCount() == 0
        assert dialog._token is None
        assert "private passphrase" not in dialog.status.text()
    finally:
        dialog.close()
        window.close()


def test_gui_session_expiry_project_switch_and_closed_dialog_revoke(
    tmp_path, qt_app,
):
    window, dbpath = setup_window(tmp_path)
    path = default_admin_credential_path(dbpath)
    create_offline_admin_credentials(path, "auditor", "separate admin password for tests")
    ticks = [100.]
    controller = OfflineAdminAuditSessions(
        path, AuthorizedReportPreviewAudit(window._project_service.database),
        clock=lambda: ticks[0],
    )
    dialog = OfflineAdminAuditDialog(
        controller, "P1", active_project=lambda: window.current_project_id,
    )
    try:
        dialog.user.setText("auditor")
        dialog.password.setText("separate admin password for tests")
        dialog.login_button.click()
        assert dialog.table.rowCount() == 25
        first = dialog._token
        ticks[0] += 901
        dialog.reload.click()
        assert dialog.stack.currentIndex() == 0
        assert dialog.table.rowCount() == 0
        with pytest.raises(PermissionError):
            controller.inspect(first, "P1")
        dialog.user.setText("auditor")
        dialog.password.setText("separate admin password for tests")
        dialog.login_button.click()
        assert dialog.table.rowCount() == 25
        second = dialog._token
        window._open_project("P2")
        dialog.reload.click()
        assert dialog._token is None
        with pytest.raises(PermissionError):
            controller.inspect(second, "P1")
    finally:
        dialog.close()
        window.close()


def test_untrusted_audit_strings_are_plain_cells_and_never_executed(tmp_path, qt_app):
    window, dbpath = setup_window(tmp_path)
    path = default_admin_credential_path(dbpath)
    create_offline_admin_credentials(path, "admin", "private passphrase for tests")
    with window._project_service.database.connect() as db:
        db.execute(
            """INSERT INTO report_release_decisions(
                project_id,report_id,inspection_started_utc,approved_by,
                approved_at_utc,review_digest,unclear_count,followup_note
            ) VALUES(?,?,?,?,?,?,?,?)""",
            ("P1", "<script>bad()</script>", "2026-10-20T10:00:00+00:00",
             "<b>untrusted</b>", "2026-10-21T11:00:00+00:00",
             "digest", 0, ""),
        )
    dialog = OfflineAdminAuditDialog(
        window._offline_admin_sessions, "P1",
        active_project=lambda: window.current_project_id,
    )
    try:
        dialog.user.setText("admin")
        dialog.password.setText("private passphrase for tests")
        dialog.login_button.click()
        assert dialog.table.item(0, 1).text() == "<script>bad()</script>"
        assert dialog.table.item(0, 2).text() == "<b>untrusted</b>"
        assert dialog.table.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers
    finally:
        dialog.close()
        window.close()
