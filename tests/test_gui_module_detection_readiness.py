"""Qt offline prerequisite audit: no invented modules, no modification.

Only synthetic DB references; the target file need not exist because the
prerequisite audit checks metadata, not RGB bytes or a model.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.services.shell_navigation import ShellRoute


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_offline_rgb_readiness_button_does_not_fabricate_modules(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "readiness.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Test RGB")
        service.create_project("P2", "Other project")
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO image_frames "
                "(project_id,frame_id,source_file,width,height) "
                "VALUES (?,?,?,?,?)",
                ("P1", "R1", "synthetic-never-opened.jpg", 800, 600),
            )
            sql.execute(
                "INSERT INTO thermal_frames "
                "(project_id,frame_id,source_file,thermal_source) "
                "VALUES (?,?,?,?)", ("P1", "T1", "synthetic-thermal.jpg", "raw"),
            )
            sql.execute(
                "INSERT INTO training_samples "
                "(sample_id,project_id,source_frame_id,source_file,modality,"
                "content_sha256,label_status,rights_status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ("S1", "P1", "R1", "synthetic-never-opened.jpg", "rgb",
                 "a" * 64, "pending", "private"),
            )
        window._open_project("P1")
        window.show_route(ShellRoute.PROCESSING)
        button = window._pages[ShellRoute.PROCESSING].findChild(
            QPushButton, "processing_check_module_readiness",
        )
        assert button is not None and button.isEnabled()
        button.click()
        status = window._pages[ShellRoute.PROCESSING].findChild(
            QLabel, "processing_module_readiness_status",
        ).text()
        assert "1 RGB-Bilder" in status
        assert "1 mit plausiblen Bildmaßen" in status
        assert "1 mit eingetragener Import-Prüfsumme" in status
        assert "1 mit beiden Metadatenvoraussetzungen" in status
        assert "Dateien hier nicht erneut gelesen" in status
        assert "keine bestätigten PV-Module" in status
        assert "synthetic-never-opened" not in status
        assert not window.action(ShellCommandId.REVIEW).isEnabled()
        assert not window.action(ShellCommandId.REPORT).isEnabled()
        assert not window.action(ShellCommandId.EXPORT).isEnabled()
        with service.database.connect() as sql:
            assert sql.execute(
                "SELECT COUNT(*) FROM pv_modules"
            ).fetchone()[0] == 0
            assert sql.execute(
                "SELECT COUNT(*) FROM offline_processing_runs"
            ).fetchone()[0] == 0

        # No stale result/callback is allowed to contaminate another project.
        window._open_project("P2")
        page = window._pages[ShellRoute.PROCESSING]
        assert not page.findChild(
            QPushButton, "processing_check_module_readiness",
        ).isEnabled()
        new_status = page.findChild(
            QLabel, "processing_module_readiness_status",
        ).text()
        assert "1 mit plausiblen Bildmaßen" not in new_status
        window._check_module_detection_readiness("P1")
        assert window._module_readiness_status is None
    finally:
        window.close()


def test_page_without_active_project_has_no_readiness_action(qt_app):
    from mcm_solarcheck.gui.processing_page import make_processing_page

    page = make_processing_page()
    try:
        assert page.findChild(
            QPushButton, "processing_check_module_readiness",
        ) is None
    finally:
        page.close()
