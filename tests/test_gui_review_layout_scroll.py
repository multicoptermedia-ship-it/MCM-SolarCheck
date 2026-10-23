"""Windows-sized review page: no squeezed controls or hidden expert decisions.

Synthetic widgets only. Viewing and scrolling must never persist approvals.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import (
    QApplication, QLabel, QListWidget, QPushButton, QScrollArea,
)

from mcm_solarcheck.gui.review_page import make_review_page


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_review_form_remains_scrollable_and_legible_at_windows_height(qt_app):
    page = make_review_page(
        current_project_id="P-PRIVATE",
        project_label="SC-0003 · Beispielanlage",
    )
    try:
        page.resize(1100, 650)
        page.show()
        qt_app.processEvents()

        scroll = page.findChild(QScrollArea, "review_workspace_scroll")
        assert scroll is not None
        assert scroll.widgetResizable()
        assert scroll.verticalScrollBar().maximum() > 0
        assert scroll.horizontalScrollBar().maximum() == 0

        # A list of review candidates must never be reduced to one clipped row.
        findings = page.findChild(QListWidget, "pending_review_findings")
        assert findings.height() >= 150

        context = page.findChild(QLabel, "review_project_context")
        assert context.text() == "Aktives Projekt: SC-0003 · Beispielanlage"

        # Explicit expert consent remains mandatory and always reachable.
        submit = page.findChild(QPushButton, "submit_expert_review")
        assert not submit.isEnabled()
        scroll.ensureWidgetVisible(submit)
        qt_app.processEvents()
        assert scroll.verticalScrollBar().value() > 0
    finally:
        page.close()


def test_legacy_project_context_keeps_opaque_identifier(qt_app):
    page = make_review_page(current_project_id="P-LEGACY")
    try:
        assert page.findChild(QLabel, "review_project_context").text() == (
            "Aktives Projekt: P-LEGACY"
        )
    finally:
        page.close()
