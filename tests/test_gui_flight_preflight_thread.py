"""Real Qt event-loop coverage for offline DJI preflight worker and lifecycle."""
import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.flight_preflight import FlightPreflightCancelled
from mcm_solarcheck.services.shell_navigation import ShellRoute


class Projects:
    def projects(self):
        return ()

    def open_project(self, project_id):
        return object()


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def make_window(qt_app):
    assert QApplication.instance() is qt_app
    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=Projects(),
    )
    window.apply_workflow_state = lambda state: None
    window._open_project("project-a")
    return window


def pump_until(predicate, *, seconds=8):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return
        QTest.qWait(12)
    assert predicate(), "DJI preflight thread did not finish within bounded test time"


def test_real_preflight_worker_returns_project_status_without_decoding_images(
    tmp_path, qt_app,
):
    folder = tmp_path / "dji"
    folder.mkdir()
    for index in range(202):
        (folder / f"DJI_20261019120000_{index:04d}_V.JPG").write_bytes(b"RGB")
        (folder / f"DJI_20261019120000_{index:04d}_T.JPG").write_bytes(b"TH")
    window = make_window(qt_app)
    try:
        window._start_flight_preflight(str(folder))
        assert window._preflight_thread is not None
        page = window._pages[ShellRoute.IMPORT]
        assert not page.findChild(
            QPushButton, "start_large_flight_preflight_button",
        ).isEnabled()
        assert page.findChild(
            QPushButton, "cancel_large_flight_preflight_button",
        ).isEnabled()
        running = window._preflight_thread
        window._start_flight_preflight(str(folder))
        assert window._preflight_thread is running
        pump_until(lambda: window._preflight_thread is None)

        page = window._pages[ShellRoute.IMPORT]
        status = page.findChild(QLabel, "large_flight_preflight_status")
        assert status is not None
        assert "202 RGB-Dateien" in status.text()
        assert "202 Thermaldateien" in status.text()
        assert "Keine Pixeldekodierung" in status.text()
        assert page.findChild(
            QPushButton, "start_large_flight_preflight_button",
        ).isEnabled()
        assert not page.findChild(
            QPushButton, "cancel_large_flight_preflight_button",
        ).isEnabled()
        assert len(list(folder.iterdir())) == 404
        assert (folder / "DJI_20261019120000_0001_V.JPG").read_bytes() == b"RGB"
    finally:
        window.close()


def test_project_switch_cancels_old_scan_and_drops_stale_result(qt_app, monkeypatch):
    import mcm_solarcheck.gui.flight_preflight_worker as worker_module

    entered = threading.Event()
    release = threading.Event()

    def blocked(folder, *, on_progress=None, should_cancel=None):
        entered.set()
        if not release.wait(timeout=5):
            raise ValueError("bounded preflight test timed out")
        if should_cancel is not None and should_cancel():
            raise FlightPreflightCancelled()
        raise AssertionError("cancelled worker unexpectedly completed")

    monkeypatch.setattr(worker_module, "scan_dji_flight_preflight", blocked)
    window = make_window(qt_app)
    try:
        window._start_flight_preflight("sample-folder")
        pump_until(entered.is_set)
        window._open_project("project-b")
        assert window.current_project_id == "project-b"
        assert "vorherigen Projekts" in window._preflight_status
        assert not window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "start_large_flight_preflight_button",
        ).isEnabled()
        release.set()
        pump_until(lambda: window._preflight_thread is None)
        assert window._preflight_status is None
        assert window._pages[ShellRoute.IMPORT].findChild(
            QLabel, "large_flight_preflight_status",
        ) is None
        assert window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "start_large_flight_preflight_button",
        ).isEnabled()
    finally:
        release.set()
        remaining = window._preflight_thread
        if remaining is not None:
            remaining.wait(5000)
            QApplication.processEvents()
        window.close()


def test_cancel_button_and_close_wait_for_native_worker(qt_app, monkeypatch):
    import mcm_solarcheck.gui.flight_preflight_worker as worker_module

    entered = threading.Event()
    release = threading.Event()

    def blocked(folder, *, on_progress=None, should_cancel=None):
        entered.set()
        if not release.wait(timeout=5):
            raise ValueError("bounded cancellation timed out")
        if should_cancel is not None and should_cancel():
            raise FlightPreflightCancelled()
        raise AssertionError("unexpected uncancelled scan")

    monkeypatch.setattr(worker_module, "scan_dji_flight_preflight", blocked)
    window = make_window(qt_app)
    window.show()
    try:
        window._start_flight_preflight("source")
        pump_until(entered.is_set)
        page = window._pages[ShellRoute.IMPORT]
        page.findChild(
            QPushButton, "cancel_large_flight_preflight_button",
        ).click()
        assert window._preflight_thread._cancel.is_set()
        window.close()
        assert window._preflight_close_pending
        assert window.isVisible()
        release.set()
        pump_until(lambda: window._preflight_thread is None and not window.isVisible())
        assert not window._preflight_close_pending
    finally:
        release.set()
        remaining = window._preflight_thread
        if remaining is not None:
            remaining.wait(5000)
            QApplication.processEvents()
        window.close()


def test_online_shell_never_exposes_unscoped_local_preflight(qt_app):
    window = SolarCheckMainWindow(
        DeploymentMode.ONLINE, project_service=Projects(),
    )
    window.apply_workflow_state = lambda state: None
    try:
        window._open_project("project-a")
        page = window._pages[ShellRoute.IMPORT]
        assert not page.findChild(
            QPushButton, "start_large_flight_preflight_button",
        ).isEnabled()
        window._start_flight_preflight("folder")
        assert window._preflight_thread is None
    finally:
        window.close()
