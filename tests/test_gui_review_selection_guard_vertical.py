"""Qt vertical regression: each pending candidate needs its own fresh choice.

Real offscreen Qt and persisted SQLite; no simulated automatic diagnosis.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import (
    QApplication, QComboBox, QLabel, QLineEdit, QListWidget, QPlainTextEdit,
    QPushButton,
)

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def populated_window(tmp_path):
    window = build_offline_window(tmp_path / "review-choice.sqlite3")
    service = window._project_service
    for project in ("P1", "P2"):
        service.create_project(project, "Synthetische Anlage")
        frame = ThermalFrame(
            frame_id="T1", source_file=Path("synthetic.jpg"),
            thermal_width=640, thermal_height=512, thermal_source="raw",
        )
        quality = ThermalQualityResult(
            ThermalQualityGrade.PASS, (),
            RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
        )
        service.database.save_thermal_frame(project, frame, quality)
        service.database.save_findings(
            project, (
                Finding("F1", "T1", 12, 25, module_id="M1"),
                Finding("F2", "T1", 14, 27, module_id="M2"),
            ),
        )
    window._open_project("P1")
    window.show_route(ShellRoute.REVIEW)
    return window


def parts(window):
    page = window._pages[ShellRoute.REVIEW]
    def find(klass, name):
        item = page.findChild(klass, name)
        assert item is not None
        return item
    return (
        find(QListWidget, "pending_review_findings"),
        find(QComboBox, "expert_decision"),
        find(QPlainTextEdit, "expert_review_note"),
        find(QLineEdit, "expert_reviewer"),
        find(QPushButton, "submit_expert_review"),
        find(QLabel, "review_selected_action"),
    )


def reviews(service, project):
    with service.database.connect() as db:
        return tuple(db.execute(
            "SELECT finding_id,status,reviewer,note "
            "FROM finding_reviews WHERE project_id=? ORDER BY finding_id",
            (project,),
        ))


def test_switch_candidate_clears_previous_review_choice_and_note(
    qt_app, tmp_path,
):
    window = populated_window(tmp_path)
    service = window._project_service
    try:
        candidates, decision, note, reviewer, submit, hint = parts(window)
        assert candidates.count() == 2
        assert decision.currentData() is None
        assert not submit.isEnabled()
        candidates.setCurrentRow(0)
        reviewer.setText("Fachgutachterin")
        decision.setCurrentIndex(1)
        note.setPlainText("Hinweis nur für F1")
        assert submit.isEnabled()
        assert "F1" in hint.text()

        candidates.setCurrentRow(1)
        assert decision.currentData() is None
        assert note.toPlainText() == ""
        assert reviewer.text() == "Fachgutachterin"
        assert not submit.isEnabled()
        assert "F2" in hint.text()
        assert "neu festlegen" in hint.text()
        assert reviews(service, "P1") == ()
        assert reviews(service, "P2") == ()

        # Returning to the previous finding does not restore its old decision.
        candidates.setCurrentRow(0)
        assert decision.currentData() is None
        assert note.toPlainText() == ""
        assert not submit.isEnabled()
        assert service.import_summary("P1").unreviewed_findings == 2
    finally:
        window.close()


def test_only_explicit_new_candidate_decision_is_saved_with_new_note(
    qt_app, tmp_path,
):
    window = populated_window(tmp_path)
    service = window._project_service
    try:
        candidates, decision, note, reviewer, submit, hint = parts(window)
        candidates.setCurrentRow(0)
        reviewer.setText("Fachgutachterin")
        decision.setCurrentIndex(1)
        note.setPlainText("Nicht auf F2 übertragen")
        candidates.setCurrentRow(1)
        assert not submit.isEnabled()
        decision.setCurrentIndex(2)
        note.setPlainText("F2 eigens geprüft")
        assert submit.isEnabled()
        submit.click()

        assert [tuple(row) for row in reviews(service, "P1")] == [
            ("F2", "rejected", "Fachgutachterin", "F2 eigens geprüft"),
        ]
        assert reviews(service, "P2") == ()
        assert service.import_summary("P1").unreviewed_findings == 1
        assert service.import_summary("P1").rejected_findings == 1
        assert service.import_summary("P2").unreviewed_findings == 2
        assert parts(window)[4].isEnabled() is False
        assert parts(window)[1].currentData() is None
        assert "F1" in parts(window)[0].item(0).text()
    finally:
        window.close()


def test_project_change_cannot_keep_old_decision_or_note(qt_app, tmp_path):
    window = populated_window(tmp_path)
    service = window._project_service
    try:
        candidates, decision, note, reviewer, submit, hint = parts(window)
        candidates.setCurrentRow(0)
        reviewer.setText("Prüferin")
        decision.setCurrentIndex(1)
        note.setPlainText("Altes Projekt")
        assert submit.isEnabled()
        window._open_project("P2")
        other = parts(window)
        assert other[0].count() == 2
        assert other[1].currentData() is None
        assert other[2].toPlainText() == ""
        assert not other[4].isEnabled()
        assert "eigen" in other[5].text() or "auswählen" in other[5].text()
        assert reviews(service, "P1") == ()
        assert reviews(service, "P2") == ()
    finally:
        window.close()
