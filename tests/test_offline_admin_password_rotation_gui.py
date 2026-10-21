"""Qt regression tests for an explicit, authenticated offline admin password change."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLineEdit

from mcm_solarcheck.gui.offline_admin_audit_dialog import OfflineAdminAuditDialog
from mcm_solarcheck.services.offline_admin_credentials import (
    create_offline_admin_credentials, default_admin_credential_path,
    verify_offline_admin_credentials,
)
from test_offline_admin_audit_gui import setup_window


OLD = "local secure existing admin password"
NEW = "another distinct and long admin password"


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def open_admin(tmp_path):
    window, dbpath = setup_window(tmp_path)
    credentials = default_admin_credential_path(dbpath)
    create_offline_admin_credentials(credentials, "audit-admin", OLD)
    dialog = OfflineAdminAuditDialog(
        window._offline_admin_sessions, "P1",
        active_project=lambda: window.current_project_id,
    )
    return window, dialog, credentials


def sign_in(dialog):
    dialog.user.setText("audit-admin")
    dialog.password.setText(OLD)
    dialog.login_button.click()
    assert dialog.stack.currentIndex() == 1
    assert dialog.table.rowCount() == 25


def test_password_fields_are_masked_and_inaccessible_without_admin_session(
    tmp_path, qt_app,
):
    window, dialog, path = open_admin(tmp_path)
    try:
        for field in (
            dialog.current_password, dialog.new_password, dialog.confirm_password,
        ):
            assert field.echoMode() is QLineEdit.EchoMode.Password
        dialog.current_password.setText(OLD)
        dialog.new_password.setText(NEW)
        dialog.confirm_password.setText(NEW)
        dialog.change_password_button.click()
        assert verify_offline_admin_credentials(path, "audit-admin", OLD)
        assert not verify_offline_admin_credentials(path, "audit-admin", NEW)
        assert dialog.table.rowCount() == 0
    finally:
        dialog.close()
        window.close()


def test_gui_password_rotation_reauthenticates_and_clears_every_secret(
    tmp_path, qt_app,
):
    window, dialog, path = open_admin(tmp_path)
    try:
        sign_in(dialog)
        token = dialog._token
        before = path.read_bytes()
        dialog.current_password.setText(OLD)
        dialog.new_password.setText(NEW)
        dialog.confirm_password.setText("typo")
        dialog.change_password_button.click()
        assert dialog.stack.currentIndex() == 1
        assert dialog._token == token
        assert path.read_bytes() == before
        assert not any([
            dialog.current_password.text(), dialog.new_password.text(),
            dialog.confirm_password.text(),
        ])

        dialog.current_password.setText(OLD)
        dialog.new_password.setText("short")
        dialog.confirm_password.setText("short")
        dialog.change_password_button.click()
        assert dialog._token == token
        assert path.read_bytes() == before

        dialog.current_password.setText(OLD)
        dialog.new_password.setText(NEW)
        dialog.confirm_password.setText(NEW)
        dialog.change_password_button.click()
        assert dialog.stack.currentIndex() == 0
        assert dialog.table.rowCount() == 0
        assert dialog._token is None
        assert verify_offline_admin_credentials(path, "audit-admin", NEW)
        assert not verify_offline_admin_credentials(path, "audit-admin", OLD)
        with pytest.raises(PermissionError):
            window._offline_admin_sessions.inspect(token, "P1")
        assert all(
            field.text() == "" for field in (
                dialog.current_password, dialog.new_password, dialog.confirm_password,
                dialog.password, dialog.user,
            )
        )
        assert OLD not in dialog.status.text()
        assert NEW not in dialog.status.text()
        dialog.user.setText("audit-admin")
        dialog.password.setText(NEW)
        dialog.login_button.click()
        assert dialog.table.rowCount() == 25
    finally:
        dialog.close()
        window.close()


def test_gui_wrong_current_password_logs_out_but_keeps_old_verifier(
    tmp_path, qt_app,
):
    window, dialog, path = open_admin(tmp_path)
    try:
        sign_in(dialog)
        before = path.read_bytes()
        dialog.current_password.setText("wrong existing password")
        dialog.new_password.setText(NEW)
        dialog.confirm_password.setText(NEW)
        dialog.change_password_button.click()
        assert dialog.stack.currentIndex() == 0
        assert dialog._token is None
        assert dialog.table.rowCount() == 0
        assert path.read_bytes() == before
        assert verify_offline_admin_credentials(path, "audit-admin", OLD)
    finally:
        dialog.close()
        window.close()


def test_gui_project_switch_rejects_password_rotation(
    tmp_path, qt_app,
):
    window, dialog, path = open_admin(tmp_path)
    try:
        sign_in(dialog)
        before = path.read_bytes()
        token = dialog._token
        window._open_project("P2")
        dialog.current_password.setText(OLD)
        dialog.new_password.setText(NEW)
        dialog.confirm_password.setText(NEW)
        dialog.change_password_button.click()
        assert dialog._token is None
        assert path.read_bytes() == before
        assert dialog.table.rowCount() == 0
        with pytest.raises(PermissionError):
            window._offline_admin_sessions.inspect(token, "P1")
    finally:
        dialog.close()
        window.close()
