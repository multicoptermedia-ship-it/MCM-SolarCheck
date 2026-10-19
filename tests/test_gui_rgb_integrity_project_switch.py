"""Project switching and busy-state regression for Windows RGB integrity UI."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute


class Projects:
    def projects(self):
        return ()

    def open_project(self, project_id):
        return object()


class PendingScan:
    def __init__(self):
        self.cancel_requests = 0

    def request_cancel(self):
        self.cancel_requests += 1


def make_window():
    app = QApplication.instance() or QApplication([])
    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=Projects(),
    )
    window.apply_workflow_state = lambda state: None
    return window


def test_switch_cancels_previous_project_and_prevents_new_scan():
    window = make_window()
    window._open_project("projekt-a")
    worker = PendingScan()
    window._integrity_thread = object()
    window._integrity_worker = worker
    window._rgb_integrity_status = "Alter Befund aus Projekt A"
    window._refresh_import_page()
    page = window._pages[ShellRoute.IMPORT]
    assert not page.findChild(QPushButton, "inspect_rgb_integrity_button").isEnabled()
    assert page.findChild(QPushButton, "cancel_rgb_integrity_button").isEnabled()

    window._open_project("projekt-b")
    assert worker.cancel_requests == 1
    assert window.current_project_id == "projekt-b"
    assert "Alter Befund" not in window._rgb_integrity_status
    assert "Vorherige RGB-Prüfung" in window._rgb_integrity_status

    # The fake busy sentinel must be cleared before closing this test window.
    window._integrity_thread = None
    window._integrity_worker = None
    window.close()


def test_completed_old_project_status_is_cleared_on_project_switch():
    window = make_window()
    window._open_project("projekt-a")
    window._rgb_integrity_status = "Prüfergebnis Projekt A"
    window._refresh_import_page()
    window._open_project("projekt-b")
    assert window._rgb_integrity_status is None
    assert window._pages[ShellRoute.IMPORT].findChild(
        QLabel, "rgb_integrity_status",
    ) is None
    window.close()
