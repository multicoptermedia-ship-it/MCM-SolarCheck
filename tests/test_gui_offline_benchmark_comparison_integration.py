"""Offline SQLite → comparison service → Qt page → exclusive JSON export."""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QPushButton

from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.offline_import_benchmark import OfflineImportBenchmarkResult
from mcm_solarcheck.services.offline_import_metrics import ImportPerformanceSnapshot
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.gui.shell import SolarCheckMainWindow


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def _button(window, name):
    result = window._pages[ShellRoute.IMPORT].findChild(QPushButton, name)
    assert result is not None
    return result


def _label(window):
    return window._pages[ShellRoute.IMPORT].findChild(
        QLabel, "offline_benchmark_comparison",
    )


def _write_valid_benchmarks(folder):
    folder.mkdir()
    paths = []
    for index in range(3):
        snapshot = ImportPerformanceSnapshot(
            elapsed_seconds=float(index + 2),
            read_and_pair_seconds=float(index + 1),
            sqlite_commit_seconds=0.5,
            observed_progress_updates=3, reported_checkpoints=50,
            process_peak_rss_bytes=(index + 3) * 1024 * 1024,
            process_peak_rss_at_start_bytes=1024 * 1024,
            outcome="succeeded",
        )
        report = OfflineImportBenchmarkResult(
            snapshot, rgb_frames=10, thermal_frames=10, image_pairs=10,
        ).anonymous_report()
        path = folder / f"PRIVATE-CUSTOMER-{index}.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        paths.append(path)
    return paths


def test_offline_desktop_user_selects_compares_then_explicitly_exports(
    qt_app, tmp_path, monkeypatch,
):
    reports = _write_valid_benchmarks(tmp_path / "PRIVATE-CUSTOMER")
    output = tmp_path / "anonymous-cohort.json"
    monkeypatch.setattr(
        QFileDialog, "getOpenFileNames",
        lambda *args, **kwargs: ([str(p) for p in reports], "JSON-Dateien (*.json)"),
    )
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *args, **kwargs: (str(output), "JSON (*.json)"),
    )

    window = build_offline_window(tmp_path / "solarcheck.sqlite3")
    try:
        window._project_service.create_project("P1", "Private-DJI-Site")
        window._project_service.create_project("P2", "Another customer")
        window._open_project("P1")
        assert _button(window, "compare_offline_benchmark_reports").isEnabled()
        assert not _button(window, "save_offline_benchmark_comparison").isEnabled()
        assert _label(window) is None
        assert not output.exists()

        _button(window, "compare_offline_benchmark_reports").click()
        QApplication.processEvents()
        label = _label(window)
        assert label is not None
        assert label.textFormat() == Qt.TextFormat.PlainText
        assert "3 Läufe" in label.text()
        assert "3.00" in label.text()
        assert "keine isolierte Importspitze" in label.text()
        assert "identische Hardware" in label.text()
        assert "PRIVATE-CUSTOMER" not in label.text()
        assert "Private-DJI-Site" not in label.text()
        assert not output.exists()
        assert _button(window, "save_offline_benchmark_comparison").isEnabled()

        _button(window, "save_offline_benchmark_comparison").click()
        assert output.is_file()
        original = output.read_bytes()
        document = json.loads(original)
        assert document["run_count"] == 3
        assert document["all_runs_succeeded"] is True
        assert document["elapsed_seconds"]["median"] == 3.0
        assert document["contains_project_or_customer_ids"] is False
        assert "PRIVATE-CUSTOMER" not in str(document)
        assert "Private-DJI-Site" not in str(document)
        _button(window, "save_offline_benchmark_comparison").click()
        assert output.read_bytes() == original
        assert "nicht gespeichert" in _label(window).text()

        stale_compare = window._pages[ShellRoute.IMPORT].findChild(
            QPushButton, "compare_offline_benchmark_reports",
        )
        window._open_project("P2")
        assert window._benchmark_comparison is None
        assert _label(window) is None
        assert not _button(window, "save_offline_benchmark_comparison").isEnabled()
        old_file = tmp_path / "stale-project.json"
        window._save_benchmark_comparison("P1", str(old_file))
        window._compare_benchmark_reports("P1", reports)
        assert not old_file.exists()
        assert window._benchmark_comparison is None
        assert window._project_service.import_summary("P1").rgb_frames == 0
        assert window._project_service.import_summary("P2").rgb_frames == 0
    finally:
        window.close()


def test_invalid_reports_cannot_keep_previous_exportable_comparison(
    qt_app, tmp_path, monkeypatch,
):
    reports = _write_valid_benchmarks(tmp_path / "PRIVATE-FLIGHT")
    window = build_offline_window(tmp_path / "work.sqlite3")
    try:
        window._project_service.create_project("P1", "Site")
        window._open_project("P1")
        window._compare_benchmark_reports("P1", reports)
        assert window._benchmark_comparison is not None
        bad = json.loads(reports[0].read_text(encoding="utf-8"))
        bad["private_flight"] = "CONFIDENTIAL-CUSTOMER-NAME"
        reports[0].write_text(json.dumps(bad), encoding="utf-8")
        window._compare_benchmark_reports("P1", reports)
        assert window._benchmark_comparison is None
        assert not _button(window, "save_offline_benchmark_comparison").isEnabled()
        assert "CONFIDENTIAL" not in _label(window).text()
        assert "PRIVATE-FLIGHT" not in _label(window).text()
        target = tmp_path / "should-not-exist.json"
        window._save_benchmark_comparison("P1", str(target))
        assert not target.exists()
    finally:
        window.close()


def test_running_import_disables_comparison_and_disallows_old_callback(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "work.sqlite3")
    try:
        window._project_service.create_project("P1", "Test")
        window._open_project("P1")
        window._import_thread = object()  # model only the busy state
        window._refresh_import_page()
        assert not _button(window, "compare_offline_benchmark_reports").isEnabled()
        window._compare_benchmark_reports("P1", [])
        assert window._benchmark_comparison is None
    finally:
        window._import_thread = None
        window.close()


def test_online_shell_has_no_local_comparison_access(qt_app):
    class Stub:
        def projects(self):
            return ()
        def open_project(self, project_id):
            return object()

    window = SolarCheckMainWindow(
        DeploymentMode.ONLINE, project_service=Stub(),
    )
    window.apply_workflow_state = lambda state: None
    try:
        window._open_project("P1")
        assert not _button(window, "compare_offline_benchmark_reports").isEnabled()
        assert not _button(window, "save_offline_benchmark_comparison").isEnabled()
        window._compare_benchmark_reports("P1", ())
        window._save_benchmark_comparison("P1", "/tmp/unwritten.json")
        assert window._benchmark_comparison is None
        assert _label(window) is None
    finally:
        window.close()
