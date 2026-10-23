"""The Windows processing page is readable and never invents completion.

All evidence is synthetic and the screen is read-only.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QScrollArea, QWidget

from mcm_solarcheck.gui.processing_page import make_processing_page
from mcm_solarcheck.services.project_pipeline import ProjectProcessingOverview
from mcm_solarcheck.services.workflow import ActionAvailability, WorkflowAction
from mcm_solarcheck.storage.queries import InspectionSummary


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def overview():
    return ProjectProcessingOverview(
        summary=InspectionSummary(
            project_id="P1",
            rgb_frames=33, thermal_frames=160, image_pairs=33,
            pv_modules=0, findings=16000, unreviewed_findings=16000,
            confirmed_findings=0, rejected_findings=0,
            unclear_findings=0, calibrated_findings=0,
        ),
        process=ActionAvailability(WorkflowAction.PROCESS, True),
        review=ActionAvailability(WorkflowAction.REVIEW, True),
    )


def test_processing_screen_keeps_import_distinct_from_finished_processing(qt_app):
    page = make_processing_page(
        current_project_id="P1",
        project_label="SC-0003 · Beispielanlage",
        overview=overview(),
    )
    try:
        page.resize(1100, 650)
        page.show()
        qt_app.processEvents()
        scroll = page.findChild(QScrollArea, "processing_workspace_scroll")
        assert scroll is not None and scroll.widgetResizable()
        assert scroll.horizontalScrollBar().maximum() == 0

        assert page.findChild(QLabel, "processing_project_context").text() == (
            "Aktives Projekt: SC-0003 · Beispielanlage"
        )
        headline_values = [
            label.text()
            for label in page.findChildren(QLabel, "processing_metric_value")
        ]
        assert headline_values == ["160", "33", "33"]
        next_steps = page.findChild(QLabel, "processing_next_steps").text()
        assert "Bilder importiert" in next_steps
        assert "Abschluss nicht nachgewiesen" in next_steps
        assert "Fachprüfung erst nach abgeschlossener Verarbeitung" in next_steps

        details = page.findChild(QWidget, "processing_details_panel")
        toggle = page.findChild(QPushButton, "processing_details_toggle")
        assert not details.isVisible()
        toggle.click()
        assert details.isVisible()
        assert "Befundkandidaten: 16000" in page.findChild(
            QLabel, "processing_persisted_evidence"
        ).text()
        toggle.click()
        assert not details.isVisible()
    finally:
        page.close()


def test_legacy_and_empty_overviews_do_not_claim_processing(qt_app):
    page = make_processing_page(current_project_id="LEGACY")
    try:
        assert page.findChild(QLabel, "processing_project_context").text() == (
            "Aktives Projekt: LEGACY"
        )
        assert page.findChild(QLabel, "processing_empty_state") is not None
        assert page.findChild(QLabel, "processing_next_steps") is None
    finally:
        page.close()
