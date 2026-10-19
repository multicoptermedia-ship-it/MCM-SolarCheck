"""Real Qt/SQLite vertical tests for cancellable DJI offline background import."""
import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

import mcm_solarcheck.services.project_pipeline as project_pipeline
from mcm_solarcheck.domain.models import Finding, ImageFrame, ImagePair, ThermalFrame
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.project_pipeline import ProjectImportCancelled
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def pump_until(predicate, *, timeout_s=10):
    until = time.monotonic() + timeout_s
    while time.monotonic() < until:
        QApplication.processEvents()
        if predicate():
            return
        QTest.qWait(12)
    assert predicate(), "DJI background import did not complete in bounded time"


def fake_import():
    rgb = ImageFrame("V-1", Path("DJI_0001_V.JPG"))
    thermal = ThermalFrame(
        frame_id="T-1", source_file=Path("DJI_0001_T.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    quality = ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5, 5, 9, 10, 9),
    )
    batch = SimpleNamespace(
        results=(SimpleNamespace(
            frame=thermal, quality=quality,
            findings=(Finding("F-1", "T-1", 1, 2),),
        ),), failures=(),
    )
    return ProjectImportResult(
        (rgb,), batch,
        (ImagePair("PAIR-1", "V-1", "T-1", 0.9, "sequence+time"),),
    )


def test_real_qt_worker_commits_sqlite_and_refreshes_import_and_review(
    qt_app, tmp_path, monkeypatch,
):
    window = build_offline_window(tmp_path / "inspection.sqlite3")
    service = window._project_service
    service.create_project("P1", "Dach Nord")
    service.create_project("P2", "Dach Sued")
    call_threads = []

    def importer(folder, *, heartbeat=None, **kwargs):
        call_threads.append(threading.get_ident())
        for _ in range(105):
            heartbeat()
        return fake_import()

    monkeypatch.setattr(project_pipeline, "import_m3t_project", importer)
    try:
        window._open_project("P1")
        assert service.import_summary("P1").rgb_frames == 0
        window._request_image_import("fake-dji-folder")
        running = window._import_thread
        assert running is not None
        page = window._pages[ShellRoute.IMPORT]
        assert not page.findChild(
            QPushButton, "import_images_button",
        ).isEnabled()
        assert page.findChild(
            QPushButton, "cancel_image_import_button",
        ).isEnabled()
        window._request_image_import("second-folder")
        assert window._import_thread is running

        pump_until(lambda: window._import_thread is None)
        assert call_threads and call_threads[0] != threading.get_ident()
        summary = service.import_summary("P1")
        assert (summary.rgb_frames, summary.thermal_frames,
                summary.findings, summary.image_pairs) == (1, 1, 1, 1)
        assert service.import_summary("P2").rgb_frames == 0
        page = window._pages[ShellRoute.IMPORT]
        assert "1 RGB" in page.findChild(QLabel, "import_summary").text()
        assert "atomar gespeichert" in page.findChild(
            QLabel, "image_import_worker_status",
        ).text()
        assert page.findChild(QPushButton, "import_images_button").isEnabled()
        assert not page.findChild(
            QPushButton, "cancel_image_import_button",
        ).isEnabled()
        assert "Ungeprüft: 1" in window._pages[ShellRoute.PROCESSING].findChild(
            QLabel, "processing_persisted_evidence",
        ).text()
    finally:
        window.close()


class BlockingProjects:
    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = []

    def projects(self):
        return ()

    def open_project(self, project_id):
        return object()

    def import_project_images_cancellable(
        self, project_id, folder, *, should_cancel=None, on_progress=None,
    ):
        self.calls.append((project_id, folder))
        self.entered.set()
        if not self.release.wait(timeout=8):
            raise ValueError("bounded mock import exceeded timeout")
        if should_cancel is not None and should_cancel():
            raise ProjectImportCancelled("cancelled")
        raise AssertionError("cancellation unexpectedly missing")


def blocking_window(qt_app):
    service = BlockingProjects()
    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=service,
    )
    window.apply_workflow_state = lambda state: None
    window._open_project("P1")
    return window, service


def settle(window, service):
    service.release.set()
    worker = window._import_thread
    if worker is not None:
        worker.request_cancel()
        worker.wait(8000)
        QApplication.processEvents()
        pump_until(lambda: window._import_thread is None, timeout_s=4)
    window.close()


def test_cancel_button_aborts_real_worker_without_reporting_success(qt_app):
    window, service = blocking_window(qt_app)
    try:
        window._request_image_import("unreadable-flight")
        pump_until(service.entered.is_set)
        page = window._pages[ShellRoute.IMPORT]
        cancel = page.findChild(QPushButton, "cancel_image_import_button")
        assert cancel.isEnabled()
        cancel.click()
        assert window._import_thread._cancel.is_set()
        service.release.set()
        pump_until(lambda: window._import_thread is None)
        page = window._pages[ShellRoute.IMPORT]
        assert "abgebrochen" in page.findChild(
            QLabel, "image_import_worker_status",
        ).text()
        assert window._last_import_attempt is None
        assert page.findChild(QPushButton, "import_images_button").isEnabled()
    finally:
        settle(window, service)


def test_project_switch_discards_stale_worker_results(qt_app):
    window, service = blocking_window(qt_app)
    try:
        window._request_image_import("flight-A")
        pump_until(service.entered.is_set)
        window._open_project("P2")
        assert window.current_project_id == "P2"
        assert window._import_thread._cancel.is_set()
        assert not window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "import_images_button",
        ).isEnabled()
        service.release.set()
        pump_until(lambda: window._import_thread is None)
        assert window._import_status is None
        assert window._last_import_attempt is None
        assert window._pages[ShellRoute.IMPORT].findChild(
            QLabel, "image_import_worker_status",
        ) is None
        assert window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "import_images_button",
        ).isEnabled()
        assert service.calls == [("P1", "flight-A")]
    finally:
        settle(window, service)


def test_close_defers_until_native_import_thread_finishes(qt_app):
    window, service = blocking_window(qt_app)
    window.show()
    try:
        window._request_image_import("flight-A")
        pump_until(service.entered.is_set)
        window.close()
        assert window._import_close_pending
        assert window.isVisible()
        assert window._import_thread._cancel.is_set()
        service.release.set()
        pump_until(lambda: window._import_thread is None and not window.isVisible())
        assert not window._import_close_pending
    finally:
        settle(window, service)


def test_online_shell_does_not_expose_unscoped_offline_import(qt_app):
    window = SolarCheckMainWindow(
        DeploymentMode.ONLINE, project_service=BlockingProjects(),
    )
    window.apply_workflow_state = lambda state: None
    try:
        window._open_project("P1")
        page = window._pages[ShellRoute.IMPORT]
        assert not page.findChild(QPushButton, "import_images_button").isEnabled()
        window._request_image_import("flight-A")
        assert window._import_thread is None
    finally:
        window.close()
