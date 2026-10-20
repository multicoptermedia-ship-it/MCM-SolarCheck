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
from mcm_solarcheck.review.findings import ReviewStatus
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



def test_selected_pending_candidate_displays_stored_evidence_without_auto_review(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "evidence.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Lokaler Solarpark")
        service.create_project("P2", "Getrenntes Projekt")
        seed_finding(service, "P1")
        seed_finding(service, "P2")
        service.database.save_findings("P1", (
            Finding(
                "F1", "T1", 23, 41, module_id="MOD-PRIV-1",
                raw_value=18500, raw_delta_from_median=235.0,
                confidence=0.8, temperature_c=87.5,
                metadata={"temperature_status": "unvalidated"},
            ),
        ))
        window._open_project("P1")
        window.show_route(ShellRoute.REVIEW)
        page = window._pages[ShellRoute.REVIEW]
        label = page.findChild(QLabel, "review_selected_evidence")
        findings = page.findChild(QListWidget, "pending_review_findings")
        assert label is not None
        assert "Bitte einen offenen Befund auswählen" in label.text()
        assert review_count(service, "P1") == 0
        assert review_count(service, "P2") == 0

        findings.setCurrentRow(0)
        assert "Befund-ID: F1" in label.text()
        assert "Thermalpixel: x=23, y=41" in label.text()
        assert "Sensorrohwert (keine °C): 18500" in label.text()
        assert "Rohwert-Abweichung vom Median: 235" in label.text()
        assert "Modulbeobachtung: MOD-PRIV-1" in label.text()
        assert "Temperatur in °C: nicht belegt" in label.text()
        assert "87.5 °C" not in label.text()
        assert not page.findChild(QPushButton, "submit_expert_review").isEnabled()
        assert review_count(service, "P1") == 0

        page.findChild(QLineEdit, "expert_reviewer").setText("Expertin")
        page.findChild(QComboBox, "expert_decision").setCurrentIndex(1)
        page.findChild(QPushButton, "submit_expert_review").click()
        assert review_count(service, "P1") == 1
        assert review_count(service, "P2") == 0
        assert service.import_summary("P1").confirmed_findings == 1
        assert service.import_summary("P2").unreviewed_findings == 1
        assert "Bitte einen offenen Befund" in window._pages[
            ShellRoute.REVIEW
        ].findChild(QLabel, "review_selected_evidence").text()
    finally:
        window.close()


def test_real_sqlite_calibrated_evidence_only_after_explicit_provenance(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "calibration.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Fiktiver Test")
        seed_finding(service, "P1")
        service.database.save_findings("P1", (
            Finding(
                "F2", "T1", 0, 12, module_id=None,
                raw_value=0, temperature_c=49.25,
                metadata={
                    "temperature_status": "calibrated",
                    "temperature_provider": "synthetic_reference",
                },
            ),
        ))
        window._open_project("P1")
        window.show_route(ShellRoute.REVIEW)
        items = window._pages[ShellRoute.REVIEW].findChild(
            QListWidget, "pending_review_findings",
        )
        assert items.count() == 2
        items.setCurrentRow(0)
        missing = window._pages[ShellRoute.REVIEW].findChild(
            QLabel, "review_selected_evidence",
        ).text()
        assert "Temperatur in °C: nicht belegt" in missing
        items.setCurrentRow(1)
        calibrated = window._pages[ShellRoute.REVIEW].findChild(
            QLabel, "review_selected_evidence",
        ).text()
        assert "49.25 °C (kalibriert; Quelle: synthetic_reference)" in calibrated
        assert "Sensorrohwert (keine °C): 0" in calibrated
        assert "Modulbeobachtung: nicht zugeordnet" in calibrated
        assert review_count(service, "P1") == 0
        assert service.import_summary("P1").unreviewed_findings == 2
    finally:
        window.close()


def test_selected_details_do_not_survive_project_switch_or_online_shell(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "isolation.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Projekt Eins")
        service.create_project("P2", "Projekt Zwei")
        seed_finding(service, "P1")
        seed_finding(service, "P2")
        service.database.save_findings("P1", (
            Finding("F1", "T1", 33, 44, module_id="PROJECT-ONE"),
        ))
        window._open_project("P1")
        window.show_route(ShellRoute.REVIEW)
        old_page = window._pages[ShellRoute.REVIEW]
        old_page.findChild(
            QListWidget, "pending_review_findings",
        ).setCurrentRow(0)
        assert "PROJECT-ONE" in old_page.findChild(
            QLabel, "review_selected_evidence",
        ).text()

        window._open_project("P2")
        new_page = window._pages[ShellRoute.REVIEW]
        label = new_page.findChild(QLabel, "review_selected_evidence")
        assert "PROJECT-ONE" not in label.text()
        assert "Bitte einen offenen Befund" in label.text()
        new_page.findChild(
            QListWidget, "pending_review_findings",
        ).setCurrentRow(0)
        assert "PROJECT-ONE" not in label.text()
        assert review_count(service, "P1") == 0

        online = SolarCheckMainWindow(
            DeploymentMode.ONLINE, project_service=service,
        )
        try:
            online._open_project("P1")
            page = online._pages[ShellRoute.REVIEW]
            assert page.findChild(
                QListWidget, "pending_review_findings",
            ).count() == 0
            assert "PROJECT-ONE" not in page.findChild(
                QLabel, "review_selected_evidence",
            ).text()
            assert not page.findChild(
                QPushButton, "submit_expert_review",
            ).isEnabled()
        finally:
            online.close()
    finally:
        window.close()


def test_old_review_page_cannot_replay_decision_after_same_project_refresh(
    qt_app, tmp_path,
):
    """Even identical project and finding IDs cannot keep an obsolete action alive."""
    window = build_offline_window(tmp_path / "same-project.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Private project")
        seed_finding(service, "P1")
        window._open_project("P1")
        old_page = window._pages[ShellRoute.REVIEW]
        old_page.findChild(QListWidget, "pending_review_findings").setCurrentRow(0)
        old_page.findChild(QLineEdit, "expert_reviewer").setText("Fachperson")
        old_page.findChild(QComboBox, "expert_decision").setCurrentIndex(1)
        old_submit = old_page.findChild(QPushButton, "submit_expert_review")
        assert old_submit.isEnabled()
        old_generation = window._review_generation

        window._refresh_review_page()
        assert window.current_project_id == "P1"
        assert window._review_generation > old_generation
        # Invoke the genuinely connected stale Qt callback, not just a mock.
        old_submit.clicked.emit()
        assert review_count(service, "P1") == 0
        assert service.import_summary("P1").unreviewed_findings == 1
        assert window._last_review_status is None

        new_page = window._pages[ShellRoute.REVIEW]
        new_page.findChild(QListWidget, "pending_review_findings").setCurrentRow(0)
        new_page.findChild(QLineEdit, "expert_reviewer").setText("Fachperson")
        new_page.findChild(QComboBox, "expert_decision").setCurrentIndex(1)
        new_page.findChild(QPushButton, "submit_expert_review").click()
        assert review_count(service, "P1") == 1
        assert service.import_summary("P1").confirmed_findings == 1
    finally:
        window.close()


def test_same_project_stale_navigation_and_preview_generation_cannot_run(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "navigation.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Private project")
        seed_finding(service, "P1")
        window._open_project("P1")
        old_gen = window._review_generation
        window._refresh_review_page()
        current_gen = window._review_generation
        assert current_gen > old_gen

        window._load_review_page("P1", 50, old_gen)
        assert window._review_offset == 0
        assert window._review_generation == current_gen
        assert window._preview_review_images(
            "P1", "F1", "/private/customer/flight", old_gen,
        ) is None
        assert review_count(service, "P1") == 0

        window._load_review_page("P1", 0, current_gen)
        assert window._review_generation == current_gen + 1
        assert window._preview_review_images(
            "P1", "F1", "/private/customer/flight", current_gen,
        ) is None
    finally:
        window.close()


def test_review_service_errors_do_not_expose_private_paths_in_qt(
    qt_app, tmp_path, monkeypatch,
):
    window = build_offline_window(tmp_path / "privacy.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Private project")
        seed_finding(service, "P1")
        window._open_project("P1")
        page = window._pages[ShellRoute.REVIEW]
        page.findChild(QListWidget, "pending_review_findings").setCurrentRow(0)
        page.findChild(QLineEdit, "expert_reviewer").setText("Fachperson")
        page.findChild(QComboBox, "expert_decision").setCurrentIndex(1)
        sentinel = "PRIVATER_KUNDENPFAD"
        def refuse(*args, **kwargs):
            raise ValueError("C:/customer/" + sentinel + "/T.JPG")
        monkeypatch.setattr(service, "review_pending_finding", refuse)

        page.findChild(QPushButton, "submit_expert_review").click()
        new_page = window._pages[ShellRoute.REVIEW]
        status = new_page.findChild(QLabel, "review_decision_status")
        assert status is not None
        assert "Entscheidung nicht gespeichert" in status.text()
        assert sentinel not in status.text()
        assert "C:/customer" not in status.text()
        assert review_count(service, "P1") == 0
        assert service.import_summary("P1").unreviewed_findings == 1
    finally:
        window.close()


def test_same_project_stale_action_cannot_review_different_paged_candidate(
    qt_app, tmp_path,
):
    window = build_offline_window(tmp_path / "offsets.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Large review")
        seed_finding(service, "P1")
        service.database.save_findings("P1", tuple(
            Finding(f"F{i:03}", "T1", i, i + 1, module_id="M1")
            for i in range(2, 54)
        ))
        window._open_project("P1")
        first_generation = window._review_generation
        window._load_review_page("P1", 50, first_generation)
        assert window._review_offset == 50
        assert window._review_generation > first_generation
        window._review_pending_finding(
            "P1", "F1", ReviewStatus.CONFIRMED, "Fachperson", None,
            expected_generation=first_generation,
        )
        window._review_pending_finding(
            "P1", "F1", ReviewStatus.CONFIRMED, "Fachperson", None,
            expected_generation=window._review_generation,
        )
        assert review_count(service, "P1") == 0
        assert service.import_summary("P1").unreviewed_findings == 53
    finally:
        window.close()
