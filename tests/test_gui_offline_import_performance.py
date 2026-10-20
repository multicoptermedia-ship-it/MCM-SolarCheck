"""Real Qt/SQLite import performance reporting without customer-data leakage."""
import json
import os
from pathlib import Path
import threading
import time
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QPushButton

import mcm_solarcheck.services.project_pipeline as pipeline
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


def pump(predicate, timeout=10):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        QApplication.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    assert predicate(), "Qt import metrics callback timed out"


def fake_import_data():
    frame = ThermalFrame(
        frame_id="T-1", source_file=Path("DJI_0001_T.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    quality = ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5, 5, 9, 10, 9),
    )
    return ProjectImportResult(
        (ImageFrame("V-1", Path("DJI_0001_V.JPG")),),
        SimpleNamespace(
            results=(SimpleNamespace(
                frame=frame, quality=quality,
                findings=(Finding("F-1", "T-1", 3, 4),),
            ),), failures=(),
        ),
        (ImagePair("PAIR-1", "V-1", "T-1", 0.9, "sequence+time"),),
    )


def test_real_import_reports_time_and_process_rss_and_exports_anonymous_json(
    qt_app, tmp_path, monkeypatch,
):
    window = build_offline_window(tmp_path / "work.sqlite3")
    service = window._project_service
    service.create_project("P1", "Kundenanlage Privat")
    service.create_project("P2", "Andere Kundenanlage")
    private_path = "VERTRAULICHE-ANLAGE-DJI-2026-10"
    seen = []

    def importer(folder, *, heartbeat=None, **kwargs):
        seen.append((folder, threading.get_ident()))
        for _ in range(55):
            heartbeat()
        return fake_import_data()

    monkeypatch.setattr(pipeline, "import_m3t_project", importer)
    export = tmp_path / "anonyme-messung.json"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *a, **k: (str(export), "JSON (*.json)"),
    )

    try:
        window._open_project("P1")
        initial = window._pages[ShellRoute.IMPORT]
        assert initial.findChild(QLabel, "offline_import_metrics") is None
        assert not initial.findChild(
            QPushButton, "save_offline_import_metrics",
        ).isEnabled()
        window._request_image_import(private_path)
        assert window._import_thread is not None
        assert not window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "save_offline_import_metrics",
        ).isEnabled()

        pump(lambda: window._import_thread is None)
        assert seen == [(private_path, seen[0][1])]
        assert seen[0][1] != threading.get_ident()
        snapshot = window._import_performance_snapshot
        assert snapshot is not None and snapshot.outcome == "succeeded"
        assert snapshot.elapsed_seconds >= 0
        assert snapshot.observed_progress_updates >= 3
        assert service.import_summary("P1").image_pairs == 1
        assert service.import_summary("P2").image_pairs == 0

        page = window._pages[ShellRoute.IMPORT]
        label = page.findChild(QLabel, "offline_import_metrics")
        assert label is not None
        assert "keine isolierte Importspitze" in label.text()
        assert private_path not in label.text()
        save = page.findChild(QPushButton, "save_offline_import_metrics")
        assert save.isEnabled()
        save.click()
        assert export.is_file()
        document = json.loads(export.read_text(encoding="utf-8"))
        assert document["outcome"] == "succeeded"
        assert document["contains_source_paths"] is False
        assert document["contains_project_or_customer_ids"] is False
        assert private_path not in export.read_text(encoding="utf-8")
        assert "Kundenanlage" not in export.read_text(encoding="utf-8")

        original = export.read_bytes()
        window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "save_offline_import_metrics",
        ).click()
        assert export.read_bytes() == original
        assert "nicht gespeichert" in window._pages[ShellRoute.IMPORT].findChild(
            QLabel, "offline_import_metrics",
        ).text()

        window._open_project("P2")
        assert window._import_performance_snapshot is None
        assert window._pages[ShellRoute.IMPORT].findChild(
            QLabel, "offline_import_metrics",
        ) is None
        assert not window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "save_offline_import_metrics",
        ).isEnabled()
        destination = tmp_path / "old-project.json"
        window._save_import_metrics("P1", str(destination))
        assert not destination.exists()
    finally:
        window.close()


class BlockingService:
    def __init__(self, *, failure=False):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.failure = failure

    def projects(self):
        return ()

    def open_project(self, _project):
        return object()

    def import_project_images_cancellable(
        self, project_id, source_folder, *, should_cancel=None, on_progress=None,
    ):
        if on_progress is not None:
            on_progress("Einlesen und Zuordnen", 0)
        self.entered.set()
        if not self.release.wait(timeout=8):
            raise ValueError("timeout waiting for synthetic test release")
        if self.failure:
            raise RuntimeError("VERTRAULICHER-KUNDE-PFAD")
        if should_cancel is not None and should_cancel():
            raise ProjectImportCancelled("cancelled before commit")
        raise AssertionError("unexpected un-cancelled operation")


def window_with_blocker(qt_app, *, failure=False):
    service = BlockingService(failure=failure)
    window = SolarCheckMainWindow(
        DeploymentMode.OFFLINE_DESKTOP, project_service=service,
    )
    window.apply_workflow_state = lambda state: None
    window._open_project("P1")
    return window, service


def cleanup(window, service):
    service.release.set()
    worker = window._import_thread
    if worker is not None:
        worker.request_cancel()
        worker.wait(8000)
        QApplication.processEvents()
        pump(lambda: window._import_thread is None, timeout=5)
    window.close()


def test_cancelled_import_keeps_anonymous_metrics_without_success_claim(qt_app):
    window, service = window_with_blocker(qt_app)
    try:
        window._request_image_import("PRIVATE-DJI-SOURCE")
        pump(service.entered.is_set)
        window._cancel_image_import()
        service.release.set()
        pump(lambda: window._import_thread is None)
        snapshot = window._import_performance_snapshot
        assert snapshot is not None and snapshot.outcome == "cancelled"
        assert window._last_import_attempt is None
        assert "cancelled" in window._pages[ShellRoute.IMPORT].findChild(
            QLabel, "offline_import_metrics",
        ).text()
        assert "PRIVATE-DJI-SOURCE" not in str(snapshot.anonymous_report())
    finally:
        cleanup(window, service)


def test_failed_import_metrics_do_not_embed_error_or_file_names(qt_app):
    window, service = window_with_blocker(qt_app, failure=True)
    try:
        window._request_image_import("SECRET-DJI-FOLDER")
        pump(service.entered.is_set)
        service.release.set()
        pump(lambda: window._import_thread is None)
        snapshot = window._import_performance_snapshot
        assert snapshot is not None and snapshot.outcome == "failed"
        report = str(snapshot.anonymous_report())
        assert "SECRET-DJI-FOLDER" not in report
        assert "VERTRAULICHER-KUNDE-PFAD" not in report
        assert window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "save_offline_import_metrics",
        ).isEnabled()
    finally:
        cleanup(window, service)


def test_project_switch_drops_old_measurement_and_old_export_callback(qt_app, tmp_path):
    window, service = window_with_blocker(qt_app)
    try:
        window._request_image_import("PRIVATE-FLIGHT")
        pump(service.entered.is_set)
        window._open_project("P2")
        service.release.set()
        pump(lambda: window._import_thread is None)
        assert window._import_performance_snapshot is None
        assert window._pages[ShellRoute.IMPORT].findChild(
            QLabel, "offline_import_metrics",
        ) is None
        previous_path = tmp_path / "should-not-write.json"
        window._save_import_metrics("P1", str(previous_path))
        assert not previous_path.exists()
    finally:
        cleanup(window, service)


def test_online_shell_does_not_offer_local_telemetry(qt_app):
    service = BlockingService()
    window = SolarCheckMainWindow(
        DeploymentMode.ONLINE, project_service=service,
    )
    window.apply_workflow_state = lambda state: None
    try:
        window._open_project("P1")
        page = window._pages[ShellRoute.IMPORT]
        assert page.findChild(QLabel, "offline_import_metrics") is None
        assert not page.findChild(
            QPushButton, "save_offline_import_metrics",
        ).isEnabled()
        assert window._import_performance_snapshot is None
    finally:
        window.close()
