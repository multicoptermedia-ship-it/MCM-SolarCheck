"""Qt vertical expert review: stored candidates -> human decision -> SQLite audit."""
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
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def seed_finding(service, project_id):
    frame = ThermalFrame(
        frame_id="T1", source_file=Path("T1.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    quality = ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )
    service.database.save_thermal_frame(project_id, frame, quality)
    service.database.save_findings(project_id, (
        Finding(
            "F1", "T1", 1, 2, module_id="M1",
            reviewer_status="unreviewed", metadata={"original": "unchanged"},
        ),
    ))


def review_count(service, project_id):
    with service.database.connect() as db:
        return db.execute(
            "SELECT COUNT(*) FROM finding_reviews WHERE project_id=?",
            (project_id,),
        ).fetchone()[0]


def test_review_page_without_project_or_service_never_enables_decisions(qt_app):
    page = make_review_page()
    try:
        assert page.objectName() == "review_page"
        assert page.findChild(QListWidget, "pending_review_findings").count() == 0
        assert not page.findChild(QPushButton, "submit_expert_review").isEnabled()
        assert not page.findChild(QPushButton, "refresh_review_button").isEnabled()
        assert page.findChild(QLabel, "review_safety_notice") is not None
    finally:
        page.close()


def test_project_scoped_human_decision_is_persisted_and_updates_review_gates(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "inspection.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Dachanlage Nord")
        service.create_project("P2", "Dachanlage Sued")
        seed_finding(service, "P1")
        seed_finding(service, "P2")

        window._open_project("P1")
        window.show_route(ShellRoute.REVIEW)
        page = window._pages[ShellRoute.REVIEW]
        assert window.current_route is ShellRoute.REVIEW
        assert "Offene Befunde: 1" in page.findChild(
            QLabel, "review_pending_count",
        ).text()
        findings = page.findChild(QListWidget, "pending_review_findings")
        assert findings.count() == 1
        assert "Modul M1" in findings.item(0).text()

        submit = page.findChild(QPushButton, "submit_expert_review")
        assert not submit.isEnabled()
        findings.setCurrentRow(0)
        assert not submit.isEnabled()
        page.findChild(QLineEdit, "expert_reviewer").setText("  Prüferin  ")
        assert not submit.isEnabled()
        page.findChild(QComboBox, "expert_decision").setCurrentIndex(1)
        assert submit.isEnabled()
        assert not window.action(ShellCommandId.REPORT).isEnabled()
        assert not window.action(ShellCommandId.EXPORT).isEnabled()
        assert review_count(service, "P1") == 0

        submit.click()
        new_page = window._pages[ShellRoute.REVIEW]
        assert window.current_route is ShellRoute.REVIEW
        assert new_page.findChild(QListWidget, "pending_review_findings").count() == 0
        assert "Offene Befunde: 0" in new_page.findChild(
            QLabel, "review_pending_count",
        ).text()
        assert "protokolliert" in new_page.findChild(
            QLabel, "review_decision_status",
        ).text()
        assert service.import_summary("P1").confirmed_findings == 1
        assert service.import_summary("P2").unreviewed_findings == 1
        assert review_count(service, "P1") == 1
        assert review_count(service, "P2") == 0
        with service.database.connect() as db:
            audit = db.execute(
                "SELECT status,reviewer FROM finding_reviews WHERE project_id='P1'"
            ).fetchone()
        assert tuple(audit) == ("confirmed", "Prüferin")
        # Readiness is only the existing persisted contract, not release.
        assert window.action(ShellCommandId.REPORT).isEnabled()

        window._open_project("P2")
        other = window._pages[ShellRoute.REVIEW]
        assert "Aktives Projekt: P2" in other.findChild(
            QLabel, "review_project_context",
        ).text()
        assert other.findChild(QListWidget, "pending_review_findings").count() == 1
        assert other.findChild(QLabel, "review_decision_status") is None
        assert not window.action(ShellCommandId.REPORT).isEnabled()
    finally:
        window.close()


def test_stale_page_cannot_apply_decision_to_new_project_with_same_finding_id(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "stale.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Projekt Eins")
        service.create_project("P2", "Projekt Zwei")
        seed_finding(service, "P1")
        seed_finding(service, "P2")
        window._open_project("P1")
        stale = window._pages[ShellRoute.REVIEW]
        stale.findChild(QListWidget, "pending_review_findings").setCurrentRow(0)
        stale.findChild(QLineEdit, "expert_reviewer").setText("Expert")
        stale.findChild(QComboBox, "expert_decision").setCurrentIndex(2)
        submit = stale.findChild(QPushButton, "submit_expert_review")
        assert submit.isEnabled()
        window._open_project("P2")
        # Old UI widgets may still receive queued events before deleteLater;
        # source-project binding must reject their decision.
        submit.click()
        assert review_count(service, "P1") == 0
        assert review_count(service, "P2") == 0
        assert service.import_summary("P2").unreviewed_findings == 1
    finally:
        window.close()


def test_online_shell_does_not_expose_unscoped_local_expert_actions(
    qt_app, tmp_path,
):
    offline = build_offline_window(tmp_path / "separate.sqlite3")
    service = offline._project_service
    service.create_project("P1", "Test")
    seed_finding(service, "P1")
    offline.close()
    online = SolarCheckMainWindow(DeploymentMode.ONLINE, project_service=service)
    try:
        online._open_project("P1")
        page = online._pages[ShellRoute.REVIEW]
        assert page.findChild(QListWidget, "pending_review_findings").count() == 0
        assert not page.findChild(QPushButton, "submit_expert_review").isEnabled()
    finally:
        online.close()
