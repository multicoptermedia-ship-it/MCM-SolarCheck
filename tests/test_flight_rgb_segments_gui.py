"""Qt presentation and worker regressions for the offline RGB segment exporter."""
import json

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture
def qapp():
    """Use the Qt runtime already installed in CI; pytest-qt is not required."""
    return QApplication.instance() or QApplication([])

from mcm_solarcheck.gui.flight_rgb_segments_worker import FlightRgbSegmentsWorker
from mcm_solarcheck.gui.import_page import make_import_page


def test_segment_button_passes_selected_folder_and_registration(qapp):
    calls = []
    page = make_import_page(
        current_project_id="p1",
        on_export_rgb_segments=lambda folder, registration: calls.append((folder, registration)),
        choose_rgb_segment_folder=lambda: "/tmp/dji",
        choose_rgb_registration=lambda: "/tmp/links.json",
    )
    page.findChild(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton,
                   "export_rgb_segments_button").click()
    assert calls == [("/tmp/dji", "/tmp/links.json")]


def test_segment_button_ignores_cancelled_selection(qapp):
    calls = []
    page = make_import_page(
        current_project_id="p1",
        on_export_rgb_segments=lambda *args: calls.append(args),
        choose_rgb_segment_folder=lambda: "",
    )
    page.findChild(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton,
                   "export_rgb_segments_button").click()
    assert calls == []


def test_worker_emits_failure_for_missing_registration(tmp_path):
    output = tmp_path / "empty"
    output.mkdir()
    worker = FlightRgbSegmentsWorker(str(tmp_path), str(tmp_path / "missing.json"), str(output))
    failures = []
    completed = []
    worker.failed.connect(failures.append)
    worker.completed.connect(lambda: completed.append(True))
    worker.run()
    assert failures
    assert completed == [True]
    assert not list(output.iterdir())


def test_worker_cancel_writes_partial_summary(tmp_path):
    output = tmp_path / "empty"
    output.mkdir()
    registration = tmp_path / "links.json"
    registration.write_text(json.dumps({
        "nonmetric_geometry": {"segments": [{"frames": {"missing": [[1,0,0],[0,1,0],[0,0,1]]}}]}
    }), encoding="utf-8")
    worker = FlightRgbSegmentsWorker(str(tmp_path), str(registration), str(output))
    results = []
    worker.finished.connect(results.append)
    worker.request_cancel()
    worker.run()
    assert results[0]["cancelled"] is True
    assert results[0]["processed"] == 0
    assert json.loads((output / "segments_summary.json").read_text())["cancelled"] is True
