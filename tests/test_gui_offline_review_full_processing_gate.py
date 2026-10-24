"""Real offline Qt shell must block Review before a verified full run.

Only synthetic records; offline tests never read or modify DJI originals.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.review.findings import ReviewStatus
from mcm_solarcheck.services.shell_commands import ShellCommandId
from mcm_solarcheck.services.shell_navigation import ShellRoute


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_offline_review_is_inaccessible_despite_imported_raw_findings(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "strict-offline.sqlite3")
    service = window._project_service
    try:
        service.create_project("P1", "Synthetische Anlage")
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO thermal_frames "
                "(project_id,frame_id,source_file,thermal_source) "
                "VALUES (?,?,?,?)", ("P1", "T1", "unopened-test.jpg", "raw"),
            )
            sql.execute(
                "INSERT INTO findings "
                "(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,"
                "finding_type,reviewer_status) VALUES (?,?,?,?,?,?,?)",
                ("P1", "F1", "T1", 1, 2, "raw_candidate", "unreviewed"),
            )
        window._open_project("P1")

        assert not window.action(ShellCommandId.REVIEW).isEnabled()
        assert not window.action(ShellCommandId.REPORT).isEnabled()
        assert not window.action(ShellCommandId.EXPORT).isEnabled()
        page = window._pages[ShellRoute.REVIEW]
        assert "Fachprüfung gesperrt" in page.findChild(
            QLabel, "review_workflow_status",
        ).text()
        assert not page.findChild(
            QPushButton, "submit_expert_review",
        ).isEnabled()

        starting_route = window.current_route
        window.show_route(ShellRoute.REVIEW)
        assert window.current_route is starting_route
        assert service.import_summary("P1").unreviewed_findings == 1

        # A direct, stale callback must be rejected by the service, not merely
        # by the disabled Qt button or blocked navigation.
        window._review_pending_finding(
            "P1", "F1", ReviewStatus.CONFIRMED, "Test Person", None,
        )
        with service.database.connect() as sql:
            assert sql.execute(
                "SELECT COUNT(*) FROM finding_reviews WHERE project_id='P1'",
            ).fetchone()[0] == 0
        assert service.import_summary("P1").confirmed_findings == 0
    finally:
        window.close()
