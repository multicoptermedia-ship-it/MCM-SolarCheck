"""Qt vertical: guarded RGB module sample, no approval or stored proposals."""
from __future__ import annotations

import os
import time
from hashlib import sha256

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")

from PIL import Image
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.services.shell_navigation import ShellRoute


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_rgb_sample_does_not_persist_modules_or_unlock_actions(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "rgb-sample.sqlite3")
    service = window._project_service
    rgb = tmp_path / "synthetic.jpg"
    Image.new("RGB", (192, 144), (130, 140, 140)).save(rgb)
    before = rgb.read_bytes()
    try:
        service.create_project("P1", "Synthetic")
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO image_frames(project_id,frame_id,source_file,width,height)"
                " VALUES (?,?,?,?,?)", ("P1", "V1", str(rgb), 192, 144),
            )
            sql.execute(
                "INSERT INTO training_samples "
                "(sample_id,project_id,source_frame_id,source_file,modality,"
                "content_sha256,label_status,rights_status)"
                " VALUES (?,?,?,?,?,?,?,?)",
                ("S1", "P1", "V1", str(rgb), "rgb",
                 sha256(before).hexdigest(), "pending", "private"),
            )
        window._open_project("P1")
        window.show_route(ShellRoute.PROCESSING)
        window.show()
        qt_app.processEvents()
        button = window._pages[ShellRoute.PROCESSING].findChild(
            QPushButton, "processing_sample_rgb_modules",
        )
        assert button is not None and button.isEnabled()
        button.click()

        deadline = time.monotonic() + 15
        while window._rgb_module_sample_thread is not None and time.monotonic() < deadline:
            qt_app.processEvents()
            time.sleep(0.01)
        qt_app.processEvents()
        assert window._rgb_module_sample_thread is None
        message = window._pages[ShellRoute.PROCESSING].findChild(
            QLabel, "processing_rgb_module_sample_status",
        ).text()
        assert "RGB-Erkennungsstichprobe beendet:" in message
        assert "1/1 ausgewertet (von 1 RGB-Bildern)" in message
        assert "0 mit Problemen" in message
        assert "Zusätzlicher Cadence-Modultest:" in message
        assert "ohne bestätigtes Raster" in message
        assert "Keine bestätigten PV-Module" in message
        assert rgb.read_bytes() == before
        for action in (
            ShellCommandId.REVIEW, ShellCommandId.REPORT, ShellCommandId.EXPORT,
        ):
            assert not window.action(action).isEnabled()
        with service.database.connect() as sql:
            for table in ("pv_modules", "offline_processing_runs", "finding_reviews"):
                assert sql.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    finally:
        window.close()


def test_cancel_and_other_preflights_mutually_exclusive(qt_app):
    from mcm_solarcheck.services.project_pipeline import ProjectProcessingOverview
    from mcm_solarcheck.services.workflow import ActionAvailability, WorkflowAction
    from mcm_solarcheck.storage.queries import InspectionSummary
    overview = ProjectProcessingOverview(
        summary=InspectionSummary(
            project_id="P1", rgb_frames=1, thermal_frames=1, image_pairs=0,
            pv_modules=0, findings=0, unreviewed_findings=0,
            confirmed_findings=0, rejected_findings=0, unclear_findings=0,
            calibrated_findings=0,
        ),
        process=ActionAvailability(WorkflowAction.PROCESS, True),
        review=ActionAvailability(WorkflowAction.REVIEW, False, ("not ready",)),
    )
    from mcm_solarcheck.gui.processing_page import make_processing_page
    cancelled = []
    page = make_processing_page(
        current_project_id="P1", overview=overview, rgb_sample_running=True,
        on_cancel_rgb_modules=lambda: cancelled.append(True),
        on_check_imported_files=lambda: None, on_check_thermal_raw=lambda: None,
        on_analyze_thermal_stats=lambda: None,
    )
    try:
        for name in (
            "processing_check_imported_files", "processing_check_thermal_raw",
            "processing_analyze_thermal_stats", "processing_sample_rgb_modules",
        ):
            assert not page.findChild(QPushButton, name).isEnabled()
        cancel = page.findChild(QPushButton, "processing_cancel_rgb_modules")
        assert cancel.isEnabled()
        cancel.click()
        assert cancelled == [True]
    finally:
        page.close()


def test_stale_project_signals_are_not_applied(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "stale.sqlite3")
    try:
        window._rgb_module_sample_project_id = "P1"
        window._current_project_id = "P2"
        window._rgb_module_sample_status = None
        window._rgb_module_sample_progress(1, 3, 0)
        window._rgb_module_sample_failed("CUSTOMER PRIVATE DATA")
        assert window._rgb_module_sample_status is None
    finally:
        window.close()
