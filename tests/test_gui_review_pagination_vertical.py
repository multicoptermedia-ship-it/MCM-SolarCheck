"""Vertical Qt expert review pagination: SQLite -> service -> UI -> audit/gates.

Synthetic findings only; no DJI hardware validation or automatic decisions.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import (
    QApplication, QComboBox, QLabel, QLineEdit, QListWidget, QPushButton,
)

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.gui.review_page import make_review_page
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def seed_page_project(service, project_id, count):
    frame = ThermalFrame(
        frame_id="T1", source_file=Path("not-a-real-flight.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    grade = ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )
    service.database.save_thermal_frame(project_id, frame, grade)
    service.database.save_findings(project_id, tuple(
        Finding(
            f"F{i:03}", "T1", i, i + 10,
            module_id="M1", reviewer_status="unreviewed",
        )
        for i in range(1, count + 1)
    ))


def ui(window, widget_class, name):
    result = window._pages[ShellRoute.REVIEW].findChild(widget_class, name)
    assert result is not None
    return result


def test_more_than_fifty_findings_are_reachable_and_human_reviewed(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "review.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Private One")
        service.create_project("P2", "Private Two")
        seed_page_project(service, "P1", 53)
        seed_page_project(service, "P2", 1)
        window._open_project("P1")
        window.show_route(ShellRoute.REVIEW)
        assert window.current_route is ShellRoute.REVIEW
        assert ui(window, QListWidget, "pending_review_findings").count() == 50
        assert ui(window, QLabel, "review_page_status").text() == (
            "Offene Befunde 1–50 von 53"
        )
        assert not ui(window, QPushButton, "review_previous_page").isEnabled()
        assert ui(window, QPushButton, "review_next_page").isEnabled()
        assert not ui(window, QPushButton, "submit_expert_review").isEnabled()
        assert not window.action(ShellCommandId.REPORT).isEnabled()
        assert service.import_summary("P1").confirmed_findings == 0

        ui(window, QPushButton, "review_next_page").click()
        pending = ui(window, QListWidget, "pending_review_findings")
        assert [pending.item(i).data(0x100) for i in range(pending.count())] == [
            "F051", "F052", "F053",
        ]
        assert ui(window, QLabel, "review_page_status").text() == (
            "Offene Befunde 51–53 von 53"
        )
        assert ui(window, QPushButton, "review_previous_page").isEnabled()
        assert not ui(window, QPushButton, "review_next_page").isEnabled()
        # Mere navigation does not create reviews or unblock reports.
        assert service.import_summary("P1").unreviewed_findings == 53
        assert not window.action(ShellCommandId.REPORT).isEnabled()

        pending.setCurrentRow(0)
        ui(window, QLineEdit, "expert_reviewer").setText("Fachprueferin")
        ui(window, QComboBox, "expert_decision").setCurrentIndex(1)
        submit = ui(window, QPushButton, "submit_expert_review")
        assert submit.isEnabled()
        submit.click()

        assert service.import_summary("P1").confirmed_findings == 1
        assert service.import_summary("P1").unreviewed_findings == 52
        assert service.import_summary("P2").unreviewed_findings == 1
        assert ui(window, QLabel, "review_page_status").text() == (
            "Offene Befunde 51–52 von 52"
        )
        assert ui(window, QListWidget, "pending_review_findings").count() == 2
        with service.database.connect() as db:
            rows = db.execute(
                "SELECT finding_id,status,reviewer FROM finding_reviews "
                "WHERE project_id=?", ("P1",),
            ).fetchall()
        assert [tuple(row) for row in rows] == [
            ("F051", "confirmed", "Fachprueferin"),
        ]
        assert not window.action(ShellCommandId.REPORT).isEnabled()

        previous = ui(window, QPushButton, "review_previous_page")
        previous.click()
        assert ui(window, QLabel, "review_page_status").text() == (
            "Offene Befunde 1–50 von 52"
        )
        window._load_review_page("P1", 50)
        assert window._review_offset == 50
        window._open_project("P2")
        assert window._review_offset == 0
        assert ui(window, QListWidget, "pending_review_findings").count() == 1
        # The page-1 callback from the other project is stale.
        window._load_review_page("P1", 50)
        assert window._review_offset == 0
        assert service.import_summary("P2").confirmed_findings == 0
    finally:
        window.close()


def test_review_page_clamps_to_first_when_last_page_disappears(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "review.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Large Project")
        seed_page_project(service, "P1", 51)
        window._open_project("P1")
        ui(window, QPushButton, "review_next_page").click()
        assert window._review_offset == 50
        assert ui(window, QListWidget, "pending_review_findings").count() == 1

        pending = ui(window, QListWidget, "pending_review_findings")
        pending.setCurrentRow(0)
        ui(window, QLineEdit, "expert_reviewer").setText("Expertin")
        ui(window, QComboBox, "expert_decision").setCurrentIndex(2)
        ui(window, QPushButton, "submit_expert_review").click()

        assert window._review_offset == 0
        assert ui(window, QListWidget, "pending_review_findings").count() == 50
        assert ui(window, QLabel, "review_page_status").text() == (
            "Offene Befunde 1–50 von 50"
        )
        assert not ui(window, QPushButton, "review_next_page").isEnabled()
        assert not window.action(ShellCommandId.REPORT).isEnabled()
    finally:
        window.close()


def test_invalid_page_requests_fail_closed_and_online_cannot_browse(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "local.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Large")
        seed_page_project(service, "P1", 52)
        window._open_project("P1")
        for offset in (True, -50, 49, 1.0, "50", None):
            window._load_review_page("P1", offset)
            assert window._review_offset == 0
        assert service.import_summary("P1").unreviewed_findings == 52

        online = SolarCheckMainWindow(
            DeploymentMode.ONLINE, project_service=service,
        )
        try:
            online._open_project("P1")
            online._load_review_page("P1", 50)
            assert online._review_offset == 0
            assert not ui(online, QPushButton, "review_next_page").isEnabled()
            assert not ui(online, QPushButton, "review_previous_page").isEnabled()
            assert not ui(online, QPushButton, "submit_expert_review").isEnabled()
            assert ui(online, QListWidget, "pending_review_findings").count() == 0
        finally:
            online.close()
    finally:
        window.close()


def test_unbound_review_page_never_navigates_or_decides(qt_app):
    page = make_review_page()
    try:
        for name in ("review_next_page", "review_previous_page", "submit_expert_review"):
            button = page.findChild(QPushButton, name)
            assert button is not None
            assert not button.isEnabled()
        assert "Keine offenen Befunde" in page.findChild(
            QLabel, "review_page_status",
        ).text()
    finally:
        page.close()


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
