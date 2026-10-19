"""Real Qt event-loop coverage of Windows RGB integrity worker lifecycle."""
import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.flight_rgb_integrity_scan import IntegrityScanCancelled
from mcm_solarcheck.services.shell_navigation import ShellRoute


class Projects:
    def projects(self):
        return ()

    def open_project(self, project_id):
        return object()


@pytest.fixture(scope="module")
def qt_app():
    """Keep a strong QApplication reference alive across real Qt thread tests."""
    app = QApplication.instance() or QApplication([])
    yield app


def window_for_project(qt_app):
    assert QApplication.instance() is qt_app
    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=Projects(),
    )
    window.apply_workflow_state = lambda state: None
    window._open_project("projekt-a")
    return window


def pump_until(predicate, *, seconds=7):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return
        QTest.qWait(15)
    assert predicate(), "Qt worker did not finish within bounded test time"


def test_real_thread_finishes_and_displays_read_only_integrity_status(tmp_path, qt_app):
    source = tmp_path / "jpeg"
    output = tmp_path / "npy"
    source.mkdir()
    output.mkdir()
    assert cv2.imwrite(
        str(source / "sample.jpg"), np.zeros((6, 8, 3), dtype=np.uint8),
    )
    window = window_for_project(qt_app)
    try:
        window._inspect_rgb_integrity(str(source), str(output))
        pump_until(lambda: getattr(window, "_integrity_thread", None) is None)
        label = window._pages[ShellRoute.IMPORT].findChild(
            QLabel, "rgb_integrity_status",
        )
        assert label is not None
        assert "Arbeitsdatei fehlt" in label.text()
        assert window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "inspect_rgb_integrity_button",
        ).isEnabled()
        assert not window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "cancel_rgb_integrity_button",
        ).isEnabled()
        assert list(output.iterdir()) == []
    finally:
        window.close()


def test_real_thread_cancel_close_and_no_duplicate_start(monkeypatch, qt_app):
    import mcm_solarcheck.gui.flight_rgb_integrity_worker as worker_module

    entered = threading.Event()
    release = threading.Event()

    def blocking_scan(source, output, *, on_progress=None, should_cancel=None):
        entered.set()
        if not release.wait(timeout=5):
            raise ValueError("bounded scan test timed out")
        if should_cancel is not None and should_cancel():
            raise IntegrityScanCancelled()
        return {"entries": [], "read_only": True}

    monkeypatch.setattr(worker_module, "scan_rgb_integrity", blocking_scan)
    window = window_for_project(qt_app)
    window.show()
    try:
        window._inspect_rgb_integrity("source", "output")
        pump_until(entered.is_set)
        running = window._integrity_thread
        page = window._pages[ShellRoute.IMPORT]
        assert not page.findChild(
            QPushButton, "inspect_rgb_integrity_button",
        ).isEnabled()
        window._inspect_rgb_integrity("another", "folder")
        assert window._integrity_thread is running

        window.close()
        assert window._integrity_close_pending
        assert window.isVisible()
        release.set()
        pump_until(lambda: window._integrity_thread is None and not window.isVisible())
        assert not window._integrity_close_pending
    finally:
        release.set()
        remaining = getattr(window, "_integrity_thread", None)
        if remaining is not None:
            remaining.quit()
            remaining.wait(5000)
            QApplication.processEvents()
        window.close()
