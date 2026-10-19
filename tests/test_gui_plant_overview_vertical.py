"""Offline plant overview vertical path: SQLite -> service -> bounded Qt inventory."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTableWidget
from PySide6.QtWidgets import QAbstractItemView

from mcm_solarcheck.domain.models import Finding, PVModule, ThermalFrame
from mcm_solarcheck.gui.plant_overview_page import make_plant_overview_page
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult
from mcm_solarcheck.vision.module_identity import IdentityAssignment, ModuleObservation


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def sample_window(tmp_path, *, module_count=2):
    window = build_offline_window(tmp_path / "overview.sqlite3")
    service = window._project_service
    service.create_project("P1", "Nord")
    service.create_project("P2", "Sued")
    frame = ThermalFrame(
        frame_id="T1", source_file=Path("T1.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    quality = ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )
    for p in ("P1", "P2"):
        service.database.save_thermal_frame(p, frame, quality)
    modules = tuple(
        PVModule(
            f"L-{i:04d}", "T1",
            ((0, 0), (10, 0), (10, 10)),
            .9, "detector",
        )
        for i in range(module_count)
    )
    service.database.save_modules("P1", modules)
    service.database.save_modules("P2", modules[:1])
    service.database.save_module_identity_assignments("P1", (
        IdentityAssignment(
            ModuleObservation("T1", "L-0000", (5, 5), 10, 10),
            "M-0001", "new", None,
        ),
    ))
    service.database.save_findings("P1", (
        Finding("F1", "T1", 1, 2, module_id="L-0000", reviewer_status="confirmed"),
        Finding("F2", "T1", 3, 4, module_id=None, reviewer_status="unreviewed"),
    ))
    service.database.save_findings("P2", (
        Finding("F1", "T1", 6, 7, module_id="L-0000", reviewer_status="rejected"),
    ))
    return window


def test_empty_page_is_read_only_and_disallows_navigation(qt_app):
    page = make_plant_overview_page()
    try:
        assert page.objectName() == "plant_overview_page"
        assert page.findChild(QLabel, "plant_empty_state") is not None
        assert page.findChild(QTableWidget, "plant_modules_table").rowCount() == 0
        assert not page.findChild(QPushButton, "plant_previous_page").isEnabled()
        assert not page.findChild(QPushButton, "plant_next_page").isEnabled()
        assert not page.findChild(QPushButton, "refresh_plant_overview").isEnabled()
        assert page.findChild(QLabel, "plant_overview_safety_notice") is not None
    finally:
        page.close()


def test_real_offline_project_renders_only_stored_module_evidence(qt_app, tmp_path):
    window = sample_window(tmp_path)
    service = window._project_service
    try:
        window._open_project("P1")
        window.show_route(ShellRoute.PLANT_OVERVIEW)
        assert window.current_route is ShellRoute.PLANT_OVERVIEW
        page = window._pages[ShellRoute.PLANT_OVERVIEW]
        summary = page.findChild(QLabel, "plant_evidence_summary").text()
        assert "Modulbeobachtungen: 2" in summary
        assert "Befundkandidaten: 2" in summary
        assert "ohne passende Modulbeobachtung: 1" in summary
        table = page.findChild(QTableWidget, "plant_modules_table")
        assert table.rowCount() == 2
        assert table.item(0, 0).text() == "L-0000"
        assert table.item(0, 4).text() == "M-0001"
        assert "algorithmisch" in table.item(0, 5).text()
        assert table.item(0, 8).text() == "1"
        assert table.item(1, 4).text() == "nicht zugeordnet"
        assert table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
        assert "kein" in page.findChild(
            QLabel, "plant_overview_safety_notice",
        ).text().lower() or "keine" in page.findChild(
            QLabel, "plant_overview_safety_notice",
        ).text().lower()

        service.database.save_findings("P1", (
            Finding("F3", "T1", 2, 3, module_id="L-0001", reviewer_status="unclear"),
        ))
        page.findChild(QPushButton, "refresh_plant_overview").click()
        assert window.current_route is ShellRoute.PLANT_OVERVIEW
        refreshed = window._pages[ShellRoute.PLANT_OVERVIEW]
        assert refreshed.findChild(QTableWidget, "plant_modules_table").item(1, 10).text() == "1"
        assert "Befundkandidaten: 3" in refreshed.findChild(
            QLabel, "plant_evidence_summary",
        ).text()

        window._open_project("P2")
        second = window._pages[ShellRoute.PLANT_OVERVIEW]
        assert "Aktives Projekt: P2" in second.findChild(
            QLabel, "plant_project_context",
        ).text()
        table = second.findChild(QTableWidget, "plant_modules_table")
        assert table.rowCount() == 1
        assert table.item(0, 4).text() == "nicht zugeordnet"
        assert table.item(0, 9).text() == "1"
        assert "Befundkandidaten: 1" in second.findChild(
            QLabel, "plant_evidence_summary",
        ).text()
        assert service.import_summary("P1").findings == 3
        assert service.import_summary("P2").findings == 1
    finally:
        window.close()


def test_large_module_inventory_is_bounded_and_previous_next_work(qt_app, tmp_path):
    window = sample_window(tmp_path, module_count=105)
    try:
        window._open_project("P1")
        window.show_route(ShellRoute.PLANT_OVERVIEW)
        first = window._pages[ShellRoute.PLANT_OVERVIEW]
        assert first.findChild(QTableWidget, "plant_modules_table").rowCount() == 100
        assert first.findChild(QPushButton, "plant_next_page").isEnabled()
        assert not first.findChild(QPushButton, "plant_previous_page").isEnabled()
        first.findChild(QPushButton, "plant_next_page").click()
        second = window._pages[ShellRoute.PLANT_OVERVIEW]
        table = second.findChild(QTableWidget, "plant_modules_table")
        assert table.rowCount() == 5
        assert table.item(0, 0).text() == "L-0100"
        assert table.item(4, 0).text() == "L-0104"
        assert second.findChild(QPushButton, "plant_previous_page").isEnabled()
        assert not second.findChild(QPushButton, "plant_next_page").isEnabled()
        second.findChild(QPushButton, "plant_previous_page").click()
        assert window._pages[ShellRoute.PLANT_OVERVIEW].findChild(
            QTableWidget, "plant_modules_table",
        ).rowCount() == 100

        # Old project callbacks cannot change the new project's page index.
        window._open_project("P2")
        window._load_plant_overview_page("P1", 100)
        assert window._plant_overview_offset == 0
        assert window._pages[ShellRoute.PLANT_OVERVIEW].findChild(
            QTableWidget, "plant_modules_table",
        ).rowCount() == 1
    finally:
        window.close()


def test_no_project_service_and_online_shell_show_no_local_data(qt_app, tmp_path):
    empty = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    try:
        page = empty._pages[ShellRoute.PLANT_OVERVIEW]
        assert page.findChild(QTableWidget, "plant_modules_table").rowCount() == 0
    finally:
        empty.close()

    offline = sample_window(tmp_path)
    service = offline._project_service
    offline.close()
    online = SolarCheckMainWindow(DeploymentMode.ONLINE, project_service=service)
    try:
        online._open_project("P1")
        overview = online._pages[ShellRoute.PLANT_OVERVIEW]
        assert overview.findChild(QTableWidget, "plant_modules_table").rowCount() == 0
        assert overview.findChild(QLabel, "plant_empty_state") is not None
        assert not overview.findChild(QPushButton, "refresh_plant_overview").isEnabled()
    finally:
        online.close()
