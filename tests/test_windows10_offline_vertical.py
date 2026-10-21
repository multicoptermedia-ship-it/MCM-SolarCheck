"""Native Windows desktop integration, Windows 10-ready release-gate probes.

Windows CI uses Server 2022, not Windows 10. These tests also run unmodified
when the Windows 10 workstation validation script is invoked with -IncludeTests.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="native Windows only")

PASSWORD = "isolated windows native administrator password"
NEXT_A = "isolated windows native replacement A"
NEXT_B = "isolated windows native replacement B"


def test_native_windows_desktop_and_admin_work_without_python_network(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication, QTableWidget

    from mcm_solarcheck.offline.entrypoint import build_offline_window
    from mcm_solarcheck.gui.offline_admin_audit_dialog import OfflineAdminAuditDialog
    from mcm_solarcheck.services.offline_admin_credentials import (
        create_offline_admin_credentials, default_admin_credential_path,
    )
    import socket

    def no_python_connection(*args, **kwargs):
        raise AssertionError("offline desktop attempted a Python network connection")

    monkeypatch.setattr(socket.socket, "connect", no_python_connection)
    monkeypatch.setattr(socket, "create_connection", no_python_connection)
    application = QApplication.instance() or QApplication([])
    database = tmp_path / "test-only.sqlite3"
    window = build_offline_window(database)
    dialog = None
    try:
        window._project_service.create_project("WIN10-LOCAL", "Temporary")
        window._open_project("WIN10-LOCAL")
        path = default_admin_credential_path(database)
        create_offline_admin_credentials(path, "operator", PASSWORD)
        dialog = OfflineAdminAuditDialog(
            window._offline_admin_sessions, "WIN10-LOCAL",
            active_project=lambda: window.current_project_id,
        )
        assert dialog.table.rowCount() == 0
        dialog.user.setText("operator")
        dialog.password.setText(PASSWORD)
        dialog.login_button.click()
        assert dialog.stack.currentIndex() == 1
        assert dialog.table.rowCount() == 0
        assert dialog.table.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers
        token = dialog._token
        window._offline_admin_sessions.change_password(token, PASSWORD, NEXT_A)
        dialog.reload.click()
        assert dialog.stack.currentIndex() == 0
        assert dialog._token is None
        assert dialog.table.rowCount() == 0
    finally:
        if dialog is not None:
            dialog.close()
        window.close()
    assert database.exists()


def test_native_windows_two_process_rotation_serializes(tmp_path):
    from mcm_solarcheck.services.offline_admin_credentials import (
        create_offline_admin_credentials, verify_offline_admin_credentials,
    )

    path = tmp_path / "native-admin.json"
    create_offline_admin_credentials(path, "operator", PASSWORD)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    worker = (
        "import json,sys; "
        "from mcm_solarcheck.services.offline_admin_credentials "
        "import rotate_offline_admin_password; "
        "args=json.loads(sys.stdin.read()); "
        "rotate_offline_admin_password(sys.argv[1], args['actor'], "
        "args['old'], args['new'])"
    )

    def run(new_password):
        command = [sys.executable, "-c", worker, str(path)]
        payload = json.dumps({
            "actor": "operator", "old": PASSWORD, "new": new_password,
        })
        # Passwords are passed on stdin, never Windows process command lines.
        return subprocess.run(
            command, input=payload, text=True,
            capture_output=True, env=env, timeout=45, check=False,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, (NEXT_A, NEXT_B)))
    assert sum(result.returncode == 0 for result in results) == 1
    assert all(
        result.returncode == 0 or "PermissionError" in result.stderr
        for result in results
    )
    assert not verify_offline_admin_credentials(path, "operator", PASSWORD)
    assert sum(
        verify_offline_admin_credentials(path, "operator", pw)
        for pw in (NEXT_A, NEXT_B)
    ) == 1
    assert not list(tmp_path.glob(".offline-admin-rotate-*"))
