"""Windows Qt image preflight: one synthetic image, never full processing.

Tests explicit controls, project isolation and source/database preservation.
"""
from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PIL import Image
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.gui.processing_page import make_processing_page
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.shell_navigation import ShellRoute


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_processing_preflight_buttons_are_not_decision_buttons(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "empty.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Fake site")
        window._open_project("P1")
        page = window._pages[ShellRoute.PROCESSING]
        button = page.findChild(QPushButton, "processing_check_imported_files")
        assert button is not None
        assert not button.isEnabled()
        assert page.findChild(QPushButton, "processing_cancel_imported_files") is None
    finally:
        window.close()


def test_local_worker_inspects_synthetic_file_without_review_or_db_changes(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "flight.sqlite3")
    source = tmp_path / "synthetic.jpg"
    Image.new("RGB", (22, 18), (12, 43, 90)).save(source)
    before = source.read_bytes()
    service = window._project_service
    try:
        service.create_project("P1", "Fake site")
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO thermal_frames "
                "(project_id,frame_id,source_file,thermal_source) "
                "VALUES (?,?,?,?)", ("P1", "T1", str(source), "palette"),
            )
        window._open_project("P1")
        window.show_route(ShellRoute.PROCESSING)
        window.show()
        qt_app.processEvents()
        page = window._pages[ShellRoute.PROCESSING]
        button = page.findChild(QPushButton, "processing_check_imported_files")
        assert button.isEnabled()
        button.click()

        limit = time.monotonic() + 8
        while window._image_check_thread is not None and time.monotonic() < limit:
            qt_app.processEvents()
            time.sleep(0.01)
        qt_app.processEvents()
        assert window._image_check_thread is None
        page = window._pages[ShellRoute.PROCESSING]
        status = page.findChild(QLabel, "processing_image_check_status").text()
        assert "Dateiprüfung beendet:" in status
        assert "1/1 strukturell lesbar" in status
        assert "keine" not in status.lower() or "fachfreigabe" in status.lower()
        assert source.read_bytes() == before
        with service.database.connect() as sql:
            assert sql.execute(
                "SELECT COUNT(*) FROM offline_processing_runs"
            ).fetchone()[0] == 0
            assert sql.execute(
                "SELECT COUNT(*) FROM finding_reviews"
            ).fetchone()[0] == 0
    finally:
        window.close()


def test_cancel_button_is_visible_only_during_active_preflight(qt_app, tmp_path):
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
            WorkflowAction.REVIEW, False, ("not processed",),
        ),
    )
    cancellations = []
    page = make_processing_page(
        overview=overview, current_project_id="P1",
        image_check_running=True,
        image_check_status="Prüfung läuft",
        on_cancel_imported_files=lambda: cancellations.append(True),
    )
    try:
        start = page.findChild(QPushButton, "processing_check_imported_files")
        cancel = page.findChild(QPushButton, "processing_cancel_imported_files")
        assert not start.isEnabled()
        assert cancel is not None and cancel.isEnabled()
        cancel.click()
        assert cancellations == [True]
    finally:
        page.close()
