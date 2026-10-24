"""Vertical Windows processing view: SQLite evidence -> service -> Qt page."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.gui.processing_page import make_processing_page
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(scope="module")
def qt_app():
    application = QApplication.instance() or QApplication([])
    yield application


def saved_thermal_frame(database, project_id):
    frame = ThermalFrame(
        frame_id="T1", source_file=Path("T1.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    quality = ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )
    database.save_thermal_frame(project_id, frame, quality)


def test_processing_page_without_service_has_no_fake_results(qt_app):
    page = make_processing_page()
    try:
        assert page.objectName() == "processing_page"
        assert page.findChild(QLabel, "processing_empty_state") is not None
        assert page.findChild(QLabel, "processing_persisted_evidence") is None
        assert page.findChild(QLabel, "processing_safety_notice") is not None
        assert not page.findChild(
            QPushButton, "refresh_processing_button",
        ).isEnabled()
    finally:
        page.close()


def test_offline_processing_page_tracks_persisted_project_and_reload(tmp_path, qt_app):
    window = build_offline_window(tmp_path / "offline.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Projekt Nord")
        service.create_project("P2", "Projekt Sued")

        window._open_project("P1")
        initial = window._pages[ShellRoute.PROCESSING]
        assert "RGB-Bilder: 0" in initial.findChild(
            QLabel, "processing_persisted_evidence",
        ).text()
        assert "Verarbeitung gesperrt" in initial.findChild(
            QLabel, "processing_workflow_status",
        ).text()
        assert not window.action(ShellCommandId.PROCESS).isEnabled()

        saved_thermal_frame(service.database, "P1")
        window._pages[ShellRoute.PROCESSING].findChild(
            QPushButton, "refresh_processing_button",
        ).click()
        assert window.action(ShellCommandId.PROCESS).isEnabled()

        window.show_route(ShellRoute.PROCESSING)
        assert window.current_route is ShellRoute.PROCESSING
        page = window._pages[ShellRoute.PROCESSING]
        evidence = page.findChild(QLabel, "processing_persisted_evidence").text()
        assert "Thermalbilder: 1" in evidence
        assert "Befundkandidaten: 0" in evidence
        assert "Fachprüfung gesperrt" in page.findChild(
            QLabel, "processing_review_status",
        ).text()

        service.database.save_findings(
            "P1", (Finding("F1", "T1", 1, 2, reviewer_status="unreviewed"),),
        )
        page.findChild(QPushButton, "refresh_processing_button").click()
        assert window.current_route is ShellRoute.PROCESSING
        page = window._pages[ShellRoute.PROCESSING]
        evidence = page.findChild(QLabel, "processing_persisted_evidence").text()
        assert "Befundkandidaten: 1" in evidence
        assert "Ungeprüft: 1" in evidence
        assert "Fachlich bestätigt: 0" in evidence
        assert "Validierte Celsiusbefunde: 0" in evidence
        assert "ein vollständiger Verarbeitungslauf wurde hier noch nicht nachgewiesen" in page.findChild(
            QLabel, "processing_review_status",
        ).text()
        assert not window.action(ShellCommandId.REPORT).isEnabled()
        assert not window.action(ShellCommandId.EXPORT).isEnabled()

        window._open_project("P2")
        page = window._pages[ShellRoute.PROCESSING]
        assert "Projekt: P2" in page.findChild(
            QLabel, "processing_project_context",
        ).text()
        assert "Thermalbilder: 0" in page.findChild(
            QLabel, "processing_persisted_evidence",
        ).text()
        assert "Befundkandidaten: 0" in page.findChild(
            QLabel, "processing_persisted_evidence",
        ).text()
        assert not window.action(ShellCommandId.PROCESS).isEnabled()
        assert service.import_summary("P1").findings == 1
        assert service.import_summary("P2").findings == 0
    finally:
        window.close()


@pytest.fixture(autouse=True)
def _simulate_completed_processing_only_for_legacy_ui_regressions(monkeypatch):
    """These historic UI tests exercise post-processing UI in isolation.

    A future trusted processing worker is simulated ONLY inside this test
    module. The real offline application remains fail-closed by default;
    tests/test_offline_review_requires_processing.py verifies that contract.
    """
    monkeypatch.setattr(
        "mcm_solarcheck.services.offline_review_gate.verified_offline_processing_blockers",
        lambda database, project_id: (),
    )
