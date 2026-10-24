"""Qt regression for real, in-memory raw sensor statistics.

Synthetic M3T-shaped test bytes, no DJI private source images.
"""
from __future__ import annotations

import os
import time
from hashlib import sha256

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.gui.processing_page import make_processing_page
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.services.shell_commands import ShellCommandId


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def segment(marker, data):
    return b"\xff" + bytes((marker,)) + (len(data) + 2).to_bytes(2, "big") + data


def synthetic_frame():
    data = (b"\x01\x00" + b"\x02\x00") * (640 * 512 // 2)
    return (
        b"fake-thermal"
        + b"".join(segment(0xE3, data[i:i+65532]) for i in range(0, len(data), 65532))
        + segment(0xE4, bytes(256)) + segment(0xE5, bytes(23818))
    )


def test_qt_statistics_run_keeps_fachpruefung_and_report_blocked(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "statistics.sqlite")
    service = window._project_service
    image = tmp_path / "synthetic.JPG"
    image.write_bytes(synthetic_frame())
    original = image.read_bytes()
    try:
        service.create_project("P1", "Testanlage")
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO thermal_frames"
                "(project_id,frame_id,source_file,thermal_source,width,height)"
                " VALUES (?,?,?,?,?,?)",
                ("P1", "T1", str(image), "raw", 640, 512),
            )
            sql.execute(
                "INSERT INTO training_samples"
                "(sample_id,project_id,source_frame_id,source_file,modality,"
                "content_sha256,label_status,rights_status)"
                " VALUES (?,?,?,?,?,?,?,?)",
                ("S1", "P1", "T1", str(image), "thermal",
                 sha256(original).hexdigest(), "pending", "private"),
            )
        window._open_project("P1")
        window.show_route(ShellRoute.PROCESSING)
        window.show()
        qt_app.processEvents()
        button = window._pages[ShellRoute.PROCESSING].findChild(
            QPushButton, "processing_analyze_thermal_stats",
        )
        assert button is not None and button.isEnabled()
        button.click()
        deadline = time.monotonic() + 12
        while window._thermal_stats_thread is not None and time.monotonic() < deadline:
            qt_app.processEvents()
            time.sleep(0.01)
        qt_app.processEvents()
        assert window._thermal_stats_thread is None
        status = window._pages[ShellRoute.PROCESSING].findChild(
            QLabel, "processing_thermal_statistics_status",
        ).text()
        assert "Thermalstatistik beendet: 1/1 Bilder statistisch ausgewertet" in status
        assert "1 mit Rohwertunterschieden" in status
        assert "0 mit Problemen" in status
        assert "Rohwertebereich: 1 bis 2 (Sensorzahlen, keine °C)" in status
        assert "Keine PV-Modulanalyse, Defektdiagnose oder Fachfreigabe" in status
        assert image.read_bytes() == original
        assert not window.action(ShellCommandId.REVIEW).isEnabled()
        assert not window.action(ShellCommandId.REPORT).isEnabled()
        assert not window.action(ShellCommandId.EXPORT).isEnabled()
        with service.database.connect() as sql:
            assert sql.execute("SELECT COUNT(*) FROM offline_processing_runs").fetchone()[0] == 0
            assert sql.execute("SELECT COUNT(*) FROM finding_reviews").fetchone()[0] == 0
    finally:
        window.close()


def test_statistics_cancel_button_and_other_scans_cannot_run_concurrently(qt_app):
    from mcm_solarcheck.services.project_pipeline import ProjectProcessingOverview
    from mcm_solarcheck.services.workflow import ActionAvailability, WorkflowAction
    from mcm_solarcheck.storage.queries import InspectionSummary

    overview = ProjectProcessingOverview(
        summary=InspectionSummary(
            project_id="P1", rgb_frames=0, thermal_frames=1, image_pairs=0,
            pv_modules=0, findings=0, unreviewed_findings=0,
            confirmed_findings=0, rejected_findings=0, unclear_findings=0,
            calibrated_findings=0,
        ),
        process=ActionAvailability(WorkflowAction.PROCESS, True),
        review=ActionAvailability(WorkflowAction.REVIEW, False, ("not ready",)),
    )
    cancellations = []
    page = make_processing_page(
        current_project_id="P1", overview=overview,
        thermal_stats_running=True,
        on_check_imported_files=lambda: None,
        on_check_thermal_raw=lambda: None,
        on_cancel_thermal_stats=lambda: cancellations.append("cancel"),
    )
    try:
        for name in (
            "processing_check_imported_files", "processing_check_thermal_raw",
            "processing_analyze_thermal_stats",
        ):
            assert not page.findChild(QPushButton, name).isEnabled()
        cancel = page.findChild(QPushButton, "processing_cancel_thermal_stats")
        assert cancel.isEnabled()
        cancel.click()
        assert cancellations == ["cancel"]
    finally:
        page.close()


def test_project_switch_ignores_stale_statistic_signals(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "stale.sqlite")
    try:
        window._thermal_stats_project_id = "P1"
        window._current_project_id = "P2"
        window._thermal_stats_status = None
        window._thermal_stats_progress(1, 1, 0)
        window._thermal_stats_failed("PRIVATE TEXT")
        assert window._thermal_stats_status is None
    finally:
        window.close()
