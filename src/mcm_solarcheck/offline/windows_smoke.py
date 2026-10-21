"""Disposable Windows/Linux offline desktop startup smoke check.

Never touches the real per-user database or initializes a production admin
identity. Does not download dependencies or open a remote network connection.
A headless Qt test is not a substitute for a Windows 10 hardware acceptance.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import tempfile
from unittest.mock import patch


def _forbid_outbound(*_args, **_kwargs):
    raise AssertionError("unexpected Python network connection in offline smoke")


def run_smoke(*, headless: bool = True) -> None:
    if headless:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    # Import Qt only after setting headless mode, so Windows CI can run
    # without a connected desktop. Never access default_database_path().
    from PySide6.QtWidgets import QApplication

    from mcm_solarcheck.offline.entrypoint import build_offline_window
    from mcm_solarcheck.services.shell_navigation import ShellRoute

    application = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="mcm-solarcheck-offline-smoke-") as folder:
        database = Path(folder) / "smoke.sqlite3"
        with patch.object(socket.socket, "connect", _forbid_outbound), patch.object(
            socket, "create_connection", _forbid_outbound
        ):
            window = build_offline_window(database)
            try:
                assert database.exists(), "smoke database must be initialized"
                assert window.current_route is ShellRoute.PROJECT
                service = window._project_service
                project_id = "OFFLINE-SMOKE"
                service.create_project(project_id, "Temporary offline acceptance test")
                window._open_project(project_id)
                assert window._current_project_id == project_id
                assert service.database is not None
                # No privileged admin access without an explicitly installed
                # credential file. No such file is ever created here.
                assert not (Path(folder) / "offline-admin-credentials.json").exists()
                # The isolated test must not publish or export any report.
            finally:
                window.close()
    # QApplication may be owned by other test code; do not quit or delete it.


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Disposable offline desktop smoke check")
    parser.add_argument("--headless", action="store_true",
                        help="Run Qt offscreen without a visible desktop")
    args = parser.parse_args(argv)
    run_smoke(headless=args.headless)
    print("Offline desktop smoke: OK (temporary project only, no Python network connection)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
