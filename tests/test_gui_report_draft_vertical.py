"""Offline Qt report/export path: reviewed SQLite findings -> explicit draft -> PDF."""
from datetime import datetime, timezone
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QComboBox, QFileDialog, QLabel, QLineEdit, QPushButton

from mcm_solarcheck.domain.models import Finding, PVModule, ThermalFrame
from mcm_solarcheck.domain.project_profile import ProjectProfile
from mcm_solarcheck.gui.export_page import make_export_page
from mcm_solarcheck.gui.report_page import make_report_page, parse_inspection_start_utc
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def seeded_window(tmp_path):
    window = build_offline_window(tmp_path / "inspection.sqlite3")
    service = window._project_service
    for project in ("P1", "P2"):
        service.create_project(project, f"Test {project}")
    service.database.save_project_profile("P1", ProjectProfile(
        "Kunde", "Solarpark", "Strasse 1", "50667", "Koeln",
        "Prueferin", site_timezone="Europe/Berlin",
    ))
    frame = ThermalFrame(
        frame_id="T1", source_file=Path("unavailable.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    quality = ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )
    service.database.save_thermal_frame("P1", frame, quality)
    service.database.save_modules("P1", (
        PVModule("M1", "T1", ((0, 0), (2, 0), (2, 2))),
    ))
    service.database.save_findings("P1", (
        Finding("F1", "T1", 2, 3, module_id="M1", reviewer_status="confirmed"),
    ))
    window._open_project("P1")
    return window


def test_timestamp_field_requires_explicit_utc():
    with pytest.raises(ValueError, match="UTC"):
        parse_inspection_start_utc("2026-10-19T12:00:00")
    with pytest.raises(ValueError, match="UTC"):
        parse_inspection_start_utc("2026-10-19T12:00:00+02:00")
    with pytest.raises(ValueError, match="ISO-8601"):
        parse_inspection_start_utc("not-a-date")
    assert parse_inspection_start_utc("2026-10-19T12:00:00+00:00") == (
        datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
    )


def test_blank_offline_pages_cannot_create_or_export(qt_app):
    report = make_report_page()
    export = make_export_page()
    try:
        assert not report.findChild(QPushButton, "prepare_report_draft").isEnabled()
        assert not export.findChild(QPushButton, "export_report_draft").isEnabled()
        assert report.findChild(QLabel, "report_draft_safety_notice") is not None
        assert export.findChild(QLabel, "export_draft_safety_notice") is not None
    finally:
        report.close()
        export.close()


def test_windows_reviewed_draft_preparation_and_local_pdf_export(tmp_path, qt_app, monkeypatch):
    window = seeded_window(tmp_path)
    out = tmp_path / "inspection-draft.pdf"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *args, **kwargs: (str(out), "Berichtsentwurf (*.pdf)"),
    )
    try:
        window.show_route(ShellRoute.REPORT)
        assert window.current_route is ShellRoute.REPORT
        report_page = window._pages[ShellRoute.REPORT]
        submit = report_page.findChild(QPushButton, "prepare_report_draft")
        assert not submit.isEnabled()
        report_page.findChild(QLineEdit, "report_draft_id").setText("ENTWURF-1")
        assert not submit.isEnabled()
        started = report_page.findChild(QLineEdit, "report_inspection_started_utc")
        started.setText("2026-10-19T12:00:00+00:00")
        assert submit.isEnabled()
        assert not out.exists()
        submit.click()
        report_page = window._pages[ShellRoute.REPORT]
        preview = report_page.findChild(QLabel, "report_draft_preview")
        assert preview is not None
        assert "Freigabestatus: draft" in preview.text()
        assert not out.exists()

        window.show_route(ShellRoute.EXPORT)
        export_page = window._pages[ShellRoute.EXPORT]
        button = export_page.findChild(QPushButton, "export_report_draft")
        assert button.isEnabled()
        assert export_page.findChild(
            QComboBox, "draft_export_format",
        ).currentData() == "pdf"
        button.click()
        assert out.is_file()
        assert out.read_bytes().startswith(b"%PDF")
        status = window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        )
        assert "draft" in status.text()
        assert window._draft_report.release_status == "draft"
        assert window._draft_report.project_id == "P1"

        # Never overwrite an existing report even if the save dialog suggests it.
        assert out.read_bytes().startswith(b"%PDF")
        contents = out.read_bytes()
        window._pages[ShellRoute.EXPORT].findChild(
            QPushButton, "export_report_draft",
        ).click()
        assert out.read_bytes() == contents
        assert "nicht gespeichert" in window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
    finally:
        window.close()


def test_project_switch_discards_report_and_export_state(tmp_path, qt_app):
    window = seeded_window(tmp_path)
    try:
        window._prepare_report_draft(
            "P1", "ENTWURF", datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
        )
        assert window._draft_report is not None
        window._open_project("P2")
        assert window._draft_report is None
        assert window._draft_request is None
        assert window._pages[ShellRoute.REPORT].findChild(
            QLabel, "report_draft_preview",
        ) is None
        assert not window._pages[ShellRoute.EXPORT].findChild(
            QPushButton, "export_report_draft",
        ).isEnabled()
        # A stale callback holding the old project must never run.
        window._prepare_report_draft(
            "P1", "STALE", datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
        )
        assert window._draft_report is None
    finally:
        window.close()


def test_revised_persisted_evidence_invalidates_old_preview(tmp_path, qt_app):
    window = seeded_window(tmp_path)
    try:
        window._prepare_report_draft(
            "P1", "ENTWURF", datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
        )
        assert window._draft_report is not None
        window._project_service.database.save_findings("P1", (
            Finding("F2", "T1", 6, 7, module_id="M1", reviewer_status="unreviewed"),
        ))
        # Even if the preview was prepared before the new finding, exporting
        # must re-run the authoritative workflow guard and discard the draft.
        window._export_offline_draft("P1", "pdf")
        assert window._draft_report is None
        assert "gesperrt" in window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
    finally:
        window.close()


def test_online_shell_has_no_unscoped_offline_report_or_export(qt_app, tmp_path):
    offline = seeded_window(tmp_path)
    service = offline._project_service
    offline.close()
    online = SolarCheckMainWindow(DeploymentMode.ONLINE, project_service=service)
    try:
        online._open_project("P1")
        assert not online._pages[ShellRoute.REPORT].findChild(
            QPushButton, "prepare_report_draft",
        ).isEnabled()
        assert not online._pages[ShellRoute.EXPORT].findChild(
            QPushButton, "export_report_draft",
        ).isEnabled()
    finally:
        online.close()


@pytest.mark.parametrize("format_name", ("pdf", "odt", "docx"))
def test_draft_export_status_does_not_show_private_save_path(
    tmp_path, qt_app, monkeypatch, format_name,
):
    """Actual Qt -> application service -> local renderer, with path-free UI."""
    window = seeded_window(tmp_path)
    private_name = f"PRIVATER_KUNDENNAME-Berichtsentwurf.{format_name}"
    destination = tmp_path / private_name
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *args, **kwargs: (str(destination), f"*.{format_name}"),
    )
    try:
        window._prepare_report_draft(
            "P1", "ENTWURF-PRIVAT", datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
        )
        assert window._draft_report is not None
        window.show_route(ShellRoute.EXPORT)
        formats = window._pages[ShellRoute.EXPORT].findChild(
            QComboBox, "draft_export_format",
        )
        formats.setCurrentIndex(formats.findData(format_name))
        button = window._pages[ShellRoute.EXPORT].findChild(
            QPushButton, "export_report_draft",
        )
        assert button.isEnabled()
        assert not destination.exists()
        button.click()
        assert destination.is_file()
        status = window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
        assert "lokal gespeichert" in status
        assert "draft" in status
        assert private_name not in status
        assert str(destination) not in status
        assert str(tmp_path) not in status
        assert window._draft_report.release_status == "draft"

        original = destination.read_bytes()
        window._pages[ShellRoute.EXPORT].findChild(
            QPushButton, "export_report_draft",
        ).click()
        assert destination.read_bytes() == original
        status = window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
        assert "nicht gespeichert" in status
        assert private_name not in status
        assert str(destination) not in status
        assert str(tmp_path) not in status
    finally:
        window.close()


def test_draft_export_errors_never_copy_exception_text_to_qt(
    tmp_path, qt_app, monkeypatch,
):
    window = seeded_window(tmp_path)
    sentinel = "VERTRAULICHER_KUNDENPFAD"
    dest = tmp_path / f"{sentinel}.pdf"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *args, **kwargs: (str(dest), "*.pdf"),
    )
    try:
        started = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
        window._prepare_report_draft("P1", "R", started)
        service = window._project_service
        def disk_failure(*args, **kwargs):
            raise OSError(f"{sentinel}: {dest}")
        monkeypatch.setattr(service, "export_offline_draft", disk_failure)
        window._export_offline_draft("P1", "pdf")
        assert not dest.exists()
        text = window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
        assert "nicht gespeichert" in text
        assert sentinel not in text
        assert str(dest) not in text
        assert window._draft_report.release_status == "draft"

        def preparation_failure(*args, **kwargs):
            raise ValueError(f"{sentinel}: {dest}")
        monkeypatch.setattr(service, "prepare_report", preparation_failure)
        window._export_offline_draft("P1", "pdf")
        assert window._draft_report is None
        text = window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
        assert "gesperrt" in text
        assert sentinel not in text
        assert str(dest) not in text
        assert not dest.exists()
    finally:
        window.close()


def test_cancelled_save_dialog_does_not_write_or_change_preview(
    tmp_path, qt_app, monkeypatch,
):
    window = seeded_window(tmp_path)
    target = tmp_path / "must-not-exist.pdf"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: ("", "*.pdf"),
    )
    try:
        window._prepare_report_draft(
            "P1", "R-CANCEL", datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
        )
        draft = window._draft_report
        window._export_offline_draft("P1", "pdf")
        assert window._draft_report is draft
        assert window._last_export_status is None
        assert not target.exists()
    finally:
        window.close()
