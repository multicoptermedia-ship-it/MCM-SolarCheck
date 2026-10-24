"""Offscreen Qt pilot of local read-only DJI raw raster inspection.

The inspected APP3 data is synthetic, not authentic DJI thermal calibration.
"""
from __future__ import annotations

import os
import time
from hashlib import sha256

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.gui.processing_page import make_processing_page
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.services.shell_navigation import ShellRoute


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def segment(marker, payload):
    return b"\xff" + bytes((marker,)) + (len(payload) + 2).to_bytes(2, "big") + payload


def raw_file_bytes():
    raw = b"\x29\x01" * (640 * 512)
    return (
        b"synthetic-start" +
        b"".join(
            segment(0xE3, raw[offset:offset + 65532])
            for offset in range(0, len(raw), 65532)
        ) +
        segment(0xE4, bytes(256)) +
        segment(0xE5, bytes(23818))
    )


def test_worker_validates_raw_bytes_but_cannot_open_review(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "raw-test.sqlite3")
    service = window._project_service
    source = tmp_path / "synthetic-m3t.JPG"
    source.write_bytes(raw_file_bytes())
    snapshot = source.read_bytes()
    try:
        service.create_project("P1", "Synthetic")
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO thermal_frames "
                "(project_id,frame_id,source_file,thermal_source,width,height) "
                "VALUES (?,?,?,?,?,?)",
                ("P1", "T1", str(source), "DJI M3T APP3 raw", 640, 512),
            )
            sql.execute(
                "INSERT INTO training_samples "
                "(sample_id,project_id,source_frame_id,source_file,modality,"
                "content_sha256,label_status,rights_status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ("S1", "P1", "T1", str(source), "thermal",
                 sha256(snapshot).hexdigest(), "unlabeled", "unverified"),
            )
        window._open_project("P1")
        window.show_route(ShellRoute.PROCESSING)
        window.show()
        qt_app.processEvents()
        button = window._pages[ShellRoute.PROCESSING].findChild(
            QPushButton, "processing_check_thermal_raw",
        )
        assert button is not None and button.isEnabled()
        button.click()

        deadline = time.monotonic() + 10
        while window._thermal_raw_thread is not None and time.monotonic() < deadline:
            qt_app.processEvents()
            time.sleep(0.01)
        qt_app.processEvents()
        assert window._thermal_raw_thread is None
        status = window._pages[ShellRoute.PROCESSING].findChild(
            QLabel, "processing_thermal_raw_status",
        ).text()
        assert "Thermal-Rohdatenprüfung beendet:" in status
        assert "1/1 16-Bit-Raster lesbar" in status
        assert "1 Import-Prüfsummen bestätigt" in status
        assert "0 mit Problemen" in status
        assert "Keine Temperaturkalibrierung" in status
        assert source.read_bytes() == snapshot
        assert not window.action(ShellCommandId.REVIEW).isEnabled()
        assert not window.action(ShellCommandId.REPORT).isEnabled()
        assert not window.action(ShellCommandId.EXPORT).isEnabled()
        with service.database.connect() as sql:
            assert sql.execute("SELECT COUNT(*) FROM offline_processing_runs").fetchone()[0] == 0
            assert sql.execute("SELECT COUNT(*) FROM finding_reviews").fetchone()[0] == 0
    finally:
        window.close()


def test_cancel_control_and_mutually_exclusive_preflight(qt_app):
    from mcm_solarcheck.services.project_pipeline import ProjectProcessingOverview
    from mcm_solarcheck.services.workflow import ActionAvailability, WorkflowAction
    from mcm_solarcheck.storage.queries import InspectionSummary

    summary = InspectionSummary(
        project_id="P1", rgb_frames=0, thermal_frames=1, image_pairs=0,
        pv_modules=0, findings=0, unreviewed_findings=0,
        confirmed_findings=0, rejected_findings=0, unclear_findings=0,
        calibrated_findings=0,
    )
    overview = ProjectProcessingOverview(
        summary=summary,
        process=ActionAvailability(WorkflowAction.PROCESS, True),
        review=ActionAvailability(
            WorkflowAction.REVIEW, False, ("Not processed",),
        ),
    )
    cancels = []
    page = make_processing_page(
        overview=overview, current_project_id="P1",
        thermal_check_running=True,
        on_cancel_thermal_raw=lambda: cancels.append("cancel"),
        on_check_imported_files=lambda: cancels.append("incorrect-read"),
    )
    try:
        raw_button = page.findChild(QPushButton, "processing_check_thermal_raw")
        cancel_button = page.findChild(
            QPushButton, "processing_cancel_thermal_raw",
        )
        check_jpeg = page.findChild(
            QPushButton, "processing_check_imported_files",
        )
        assert raw_button is not None and not raw_button.isEnabled()
        assert check_jpeg is not None and not check_jpeg.isEnabled()
        assert cancel_button is not None and cancel_button.isEnabled()
        cancel_button.click()
        assert cancels == ["cancel"]
    finally:
        page.close()


def test_stale_project_callback_does_not_publish_into_another_project(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "project-raw.sqlite3")
    try:
        window._thermal_raw_project_id = "P1"
        window._current_project_id = "P2"
        window._thermal_raw_status = None
        window._thermal_raw_check_progress(1, 1, 0)
        assert window._thermal_raw_status is None
        window._thermal_raw_check_failed("DO NOT SHOW")
        assert window._thermal_raw_status is None
    finally:
        window.close()
