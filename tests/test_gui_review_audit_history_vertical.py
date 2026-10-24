"""Vertical Qt/SQLite audit history: human decision -> persisted event -> readonly pages.

Uses synthetic inspection data and a headless Qt runtime, not DJI or Windows.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QLabel, QListWidget, QPushButton,
)

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.review.findings import ReviewStatus
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def prepared(tmp_path, *, completed=28):
    window = build_offline_window(tmp_path / "audit-history.sqlite3")
    service = window._project_service
    for project in ("P1", "P2"):
        service.create_project(project, "Synthetischer Solarpark")
        service.database.save_thermal_frame(
            project,
            ThermalFrame(
                frame_id="T1", source_file=Path("synthetic.JPG"),
                thermal_width=640, thermal_height=512, thermal_source="raw",
            ),
            ThermalQualityResult(
                ThermalQualityGrade.PASS, (),
                RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
            ),
        )
        service.database.save_findings(project, tuple(
            Finding(f"F{i:03}", "T1", i, 2 * i, module_id="M1")
            for i in range(1, 34)
        ))
    for i in range(1, completed + 1):
        service.review_pending_finding(
            "P1", f"F{i:03}",
            status=(ReviewStatus.CONFIRMED if i % 2 else ReviewStatus.UNCLEAR),
            reviewer="Prüferin A",
            note=f"Fachnotiz {i}" if i != 1 else "<Privater Text & Prüfnachweis>",
        )
    service.review_pending_finding(
        "P2", "F001", status=ReviewStatus.REJECTED,
        reviewer="Prüfer B", note="Nur Projekt P2",
    )
    window._open_project("P1")
    window.show_route(ShellRoute.REVIEW)
    return window


def get(window, klass, name):
    item = window._pages[ShellRoute.REVIEW].findChild(klass, name)
    assert item is not None
    return item


def audit_rows(service, project):
    with service.database.connect() as db:
        return tuple(db.execute(
            "SELECT review_id,finding_id,status,note FROM finding_reviews "
            "WHERE project_id=? ORDER BY review_id", (project,),
        ))


def test_qt_history_is_readonly_and_shows_actual_persisted_decisions(
    tmp_path, qt_app,
):
    window = prepared(tmp_path)
    service = window._project_service
    try:
        before = audit_rows(service, "P1")
        assert get(window, QLabel, "review_history_count").text() == (
            "Dokumentierte Entscheidungen: 28 · Angezeigt: 25 (maximal 25)"
        )
        history = get(window, QListWidget, "review_history_events")
        assert history.count() == 25
        assert "F028" in history.item(0).text()
        assert "F004" in history.item(24).text()
        assert "Prüferin A" in history.item(0).text()
        assert get(window, QLabel, "review_history_selected").text() == (
            "Bitte eine dokumentierte Entscheidung auswählen."
        )
        history.setCurrentRow(0)
        details = get(window, QLabel, "review_history_selected")
        assert "Befund: F028" in details.text()
        assert "Status bei dieser Entscheidung: unclear" in details.text()
        assert "Fachnotiz 28" in details.text()
        assert details.textFormat() == Qt.TextFormat.PlainText
        assert get(window, QPushButton, "review_history_next").isEnabled()
        assert not get(window, QPushButton, "review_history_previous").isEnabled()
        assert len(audit_rows(service, "P1")) == len(before)
        assert audit_rows(service, "P1") == before
        assert not window.action(ShellCommandId.REPORT).isEnabled()
        assert service.import_summary("P1").unreviewed_findings == 5
    finally:
        window.close()


def test_qt_history_can_reach_older_events_and_preserves_user_note_as_text(
    tmp_path, qt_app,
):
    window = prepared(tmp_path)
    service = window._project_service
    before = audit_rows(service, "P1")
    try:
        get(window, QPushButton, "review_history_next").click()
        assert get(window, QLabel, "review_history_page_status").text() == (
            "Entscheidungen 26–28 von 28"
        )
        history = get(window, QListWidget, "review_history_events")
        assert history.count() == 3
        assert [history.item(i).text().split(" · ")[0] for i in range(3)] == [
            "F003", "F002", "F001",
        ]
        history.setCurrentRow(2)
        detail = get(window, QLabel, "review_history_selected")
        assert "<Privater Text & Prüfnachweis>" in detail.text()
        assert detail.textFormat() == Qt.TextFormat.PlainText
        assert get(window, QPushButton, "review_history_previous").isEnabled()
        assert not get(window, QPushButton, "review_history_next").isEnabled()
        get(window, QPushButton, "review_history_previous").click()
        assert window._review_history_offset == 0
        assert audit_rows(service, "P1") == before
    finally:
        window.close()


def test_history_resets_on_project_switch_and_rejects_old_buttons(
    tmp_path, qt_app,
):
    window = prepared(tmp_path)
    service = window._project_service
    try:
        old_forward = get(window, QPushButton, "review_history_next")
        old_forward.click()
        assert window._review_history_offset == 25
        old_backward = get(window, QPushButton, "review_history_previous")
        window._open_project("P2")
        assert window._review_history_offset == 0
        assert get(window, QListWidget, "review_history_events").count() == 1
        get(window, QListWidget, "review_history_events").setCurrentRow(0)
        assert "Nur Projekt P2" in get(
            window, QLabel, "review_history_selected",
        ).text()
        assert "F028" not in get(
            window, QLabel, "review_history_selected",
        ).text()
        old_forward.clicked.emit()
        old_backward.clicked.emit()
        assert window._review_history_offset == 0
        assert audit_rows(service, "P2") and len(audit_rows(service, "P2")) == 1
    finally:
        window.close()


def test_history_navigation_from_stale_same_project_qt_generation_does_nothing(
    tmp_path, qt_app,
):
    window = prepared(tmp_path)
    service = window._project_service
    try:
        old_forward = get(window, QPushButton, "review_history_next")
        initial_generation = window._review_generation
        window._refresh_review_page()
        assert window._review_generation > initial_generation
        old_forward.clicked.emit()
        assert window._review_history_offset == 0
        assert window._review_generation == initial_generation + 1
        assert get(window, QLabel, "review_history_page_status").text() == (
            "Entscheidungen 1–25 von 28"
        )
        assert len(audit_rows(service, "P1")) == 28
    finally:
        window.close()


def test_online_shell_cannot_see_local_review_audit_history(
    tmp_path, qt_app,
):
    offline = prepared(tmp_path)
    service = offline._project_service
    offline.close()
    online = SolarCheckMainWindow(
        DeploymentMode.ONLINE, project_service=service,
    )
    try:
        online._open_project("P1")
        assert get(online, QListWidget, "review_history_events").count() == 0
        assert not get(online, QPushButton, "review_history_previous").isEnabled()
        assert not get(online, QPushButton, "review_history_next").isEnabled()
        assert "Prüferin A" not in get(
            online, QLabel, "review_history_count",
        ).text()
        online._load_review_history_page("P1", 25)
        assert online._review_history_offset == 0
        assert len(audit_rows(service, "P1")) == 28
    finally:
        online.close()


def test_history_page_remains_consistent_after_new_human_review(
    tmp_path, qt_app,
):
    window = prepared(tmp_path)
    service = window._project_service
    try:
        assert get(window, QLabel, "review_history_count").text().startswith(
            "Dokumentierte Entscheidungen: 28"
        )
        service.review_pending_finding(
            "P1", "F029", status=ReviewStatus.REJECTED,
            reviewer="Zweiter Prüfer", note="Neue bewusste Entscheidung",
        )
        window._refresh_review_page()
        assert get(window, QLabel, "review_history_count").text().startswith(
            "Dokumentierte Entscheidungen: 29"
        )
        history = get(window, QListWidget, "review_history_events")
        assert "F029" in history.item(0).text()
        history.setCurrentRow(0)
        assert "Neue bewusste Entscheidung" in get(
            window, QLabel, "review_history_selected",
        ).text()
        assert service.import_summary("P1").unreviewed_findings == 4
        assert len(audit_rows(service, "P1")) == 29
        assert not window.action(ShellCommandId.REPORT).isEnabled()
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
