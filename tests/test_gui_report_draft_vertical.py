"""Offline Qt report/export path: reviewed SQLite findings -> explicit draft -> PDF."""
from datetime import datetime, timezone
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QFileDialog, QLabel, QLineEdit, QPushButton

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


def test_modal_project_switch_blocks_stale_report(tmp_path, qt_app, monkeypatch):
    window = seeded_window(tmp_path)
    target = tmp_path / "PRIVATER_KUNDENNAME-P1.pdf"
    try:
        window._prepare_report_draft(
            "P1", "OLD", datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
        )
        def change_project(*_a, **_k):
            window._open_project("P2")
            return str(target), "*.pdf"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", change_project)
        window._export_offline_draft("P1", "pdf")
        assert window.current_project_id == "P2"
        assert window._draft_report is None
        assert window._last_export_status is None
        assert not target.exists()
    finally:
        window.close()


def test_modal_replacement_draft_cannot_export_previous_preview(
    tmp_path, qt_app, monkeypatch,
):
    window = seeded_window(tmp_path)
    target = tmp_path / "PRIVATER_KUNDENNAME-OLD.pdf"
    started = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
    try:
        window._prepare_report_draft("P1", "OLD", started)
        def prepare_new(*_a, **_k):
            window._prepare_report_draft("P1", "NEW", started)
            return str(target), "*.pdf"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", prepare_new)
        window._export_offline_draft("P1", "pdf")
        assert not target.exists()
        assert window._draft_report is not None
        assert window._draft_report.report_id == "NEW"
        assert window._last_export_status is None
    finally:
        window.close()


def test_modal_evidence_change_requires_new_draft(tmp_path, qt_app, monkeypatch):
    window = seeded_window(tmp_path)
    target = tmp_path / "PRIVATER_KUNDENNAME-changed.pdf"
    try:
        window._prepare_report_draft(
            "P1", "OLD", datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
        )
        def change_profile(*_a, **_k):
            window._project_service.database.save_project_profile(
                "P1", ProjectProfile(
                    "Kunde", "Solarpark geaendert", "Strasse 1", "50667",
                    "Koeln", "Prueferin", site_timezone="Europe/Berlin",
                ),
            )
            return str(target), "*.pdf"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", change_profile)
        window._export_offline_draft("P1", "pdf")
        assert not target.exists()
        assert window._draft_report is None
        assert window._draft_request is None
        message = window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
        assert "gesperrt" in message
        assert "PRIVATER_KUNDENNAME" not in message
    finally:
        window.close()


def test_relative_report_destination_fails_without_implicit_cwd_path(
    tmp_path, qt_app, monkeypatch,
):
    window = seeded_window(tmp_path)
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "PRIVATER_KUNDENNAME-relative.pdf"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *_a, **_k: (target.name, "*.pdf"),
    )
    try:
        window._prepare_report_draft(
            "P1", "READY", datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
        )
        window._export_offline_draft("P1", "pdf")
        assert not target.exists()
        message = window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
        assert "nicht gespeichert" in message
        assert "PRIVATER_KUNDENNAME" not in message
    finally:
        window.close()


def test_release_requires_separate_human_action_not_a_full_review(tmp_path, qt_app):
    """100% stored decisions permit a draft, never an automatic released report."""
    window = seeded_window(tmp_path)
    try:
        started = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
        window._prepare_report_draft("P1", "R-EXPLICIT", started)
        assert window._draft_report.release_status == "draft"
        with pytest.raises(PermissionError, match="human release"):
            window._project_service.prepare_report(
                "P1", "R-EXPLICIT", started, release_status="released",
            )
        report = window._pages[ShellRoute.REPORT]
        assert not report.findChild(QPushButton, "approve_report_release").isEnabled()
        export = window._pages[ShellRoute.EXPORT]
        assert not export.findChild(QPushButton, "export_report_released").isEnabled()
        with window._project_service.database.connect() as sql:
            assert sql.execute(
                "SELECT COUNT(*) FROM report_release_decisions"
            ).fetchone()[0] == 0
    finally:
        window.close()


def test_explicit_offline_qt_signoff_and_released_pdf(tmp_path, qt_app, monkeypatch):
    window = seeded_window(tmp_path)
    output = tmp_path / "local-released.pdf"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        lambda *_a, **_k: (str(output), "Freigegebener Bericht (*.pdf)"),
    )
    started = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
    try:
        window._prepare_report_draft("P1", "RELEASE-1", started)
        page = window._pages[ShellRoute.REPORT]
        page.findChild(QLineEdit, "report_release_reviewer").setText("Fachprüferin")
        action = page.findChild(QPushButton, "approve_report_release")
        assert action.isEnabled()
        assert not output.exists()
        action.click()
        with window._project_service.database.connect() as sql:
            record = sql.execute(
                """SELECT project_id,report_id,approved_by,unclear_count
                   FROM report_release_decisions"""
            ).fetchone()
            assert tuple(record) == ("P1", "RELEASE-1", "Fachprüferin", 0)
        page = window._pages[ShellRoute.REPORT]
        assert "Fachprüferin" in page.findChild(QLabel, "report_release_status").text()
        assert not page.findChild(QPushButton, "approve_report_release").isEnabled()
        report = window._project_service.prepare_report(
            "P1", "RELEASE-1", started, release_status="released",
        )
        assert report.release_status == "released"
        assert window._draft_report.release_status == "draft"
        export = window._pages[ShellRoute.EXPORT]
        publish = export.findChild(QPushButton, "export_report_released")
        assert publish.isEnabled()
        publish.click()
        assert output.read_bytes().startswith(b"%PDF")
        assert "released" in window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
        assert str(tmp_path) not in window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
        assert window._draft_report.release_status == "draft"

        original = output.read_bytes()
        window._export_offline_released("P1", "pdf")
        assert output.read_bytes() == original
        assert "nicht gespeichert" in window._pages[ShellRoute.EXPORT].findChild(
            QLabel, "report_export_status",
        ).text()
    finally:
        window.close()


def test_unclear_report_needs_explicit_followup_and_stays_visible(tmp_path, qt_app):
    window = seeded_window(tmp_path)
    from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP
    started = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
    try:
        window._project_service.database.save_findings(
            "P1", (Finding("F2", "T1", 4, 5, module_id="M1",
                           reviewer_status="unclear"),),
        )
        window._prepare_report_draft("P1", "RELEASE-UNCLEAR", started)
        page = window._pages[ShellRoute.REPORT]
        page.findChild(QLineEdit, "report_release_reviewer").setText("Prueferin")
        action = page.findChild(QPushButton, "approve_report_release")
        assert not action.isEnabled()
        with pytest.raises(ValueError, match="follow-up"):
            window._project_service.approve_offline_report(
                "P1", "RELEASE-UNCLEAR", started, capabilities=OFFLINE_DESKTOP,
                approved_by="Prueferin",
            )
        page.findChild(QCheckBox, "report_release_unclear_ack").setChecked(True)
        assert not action.isEnabled()
        page.findChild(QLineEdit, "report_release_followup_note").setText(
            "Zweite Messung für M1 veranlassen",
        )
        assert action.isEnabled()
        action.click()
        decision = window._project_service.report_release_decision(
            "P1", "RELEASE-UNCLEAR", started,
        )
        assert decision.unclear_count == 1
        assert "Zweite Messung" in decision.followup_note
        assert window._project_service.prepare_report(
            "P1", "RELEASE-UNCLEAR", started, release_status="released",
        ).manual_review_modules == 1
    finally:
        window.close()


def test_changed_project_evidence_invalidates_release_and_blocks_export(
    tmp_path, qt_app, monkeypatch,
):
    window = seeded_window(tmp_path)
    from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP
    started = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
    try:
        window._prepare_report_draft("P1", "R-STALE", started)
        service = window._project_service
        service.approve_offline_report(
            "P1", "R-STALE", started, capabilities=OFFLINE_DESKTOP,
            approved_by="Prueferin", expected_draft=window._draft_report,
        )
        service.database.save_project_profile("P1", ProjectProfile(
            "Kunde", "Solarpark geaendert", "Strasse 1", "50667", "Koeln",
            "Prueferin", site_timezone="Europe/Berlin",
        ))
        assert service.report_release_decision("P1", "R-STALE", started) is None
        target = tmp_path / "should-not-be-written.pdf"
        with pytest.raises((PermissionError, ValueError)):
            service.export_offline_released(
                "P1", "R-STALE", started, target,
                capabilities=OFFLINE_DESKTOP,
                expected_draft=window._draft_report,
            )
        assert not target.exists()
        window._refresh_export_page()
        assert not window._pages[ShellRoute.EXPORT].findChild(
            QPushButton, "export_report_released",
        ).isEnabled()
        with service.database.connect() as sql:
            assert sql.execute(
                "SELECT COUNT(*) FROM report_release_decisions"
            ).fetchone()[0] == 1
    finally:
        window.close()


def test_project_change_in_release_save_dialog_never_exports(
    tmp_path, qt_app, monkeypatch,
):
    window = seeded_window(tmp_path)
    from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP
    started = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
    target = tmp_path / "do-not-export.pdf"
    try:
        window._prepare_report_draft("P1", "R-OLD", started)
        window._project_service.approve_offline_report(
            "P1", "R-OLD", started, capabilities=OFFLINE_DESKTOP,
            approved_by="Prueferin", expected_draft=window._draft_report,
        )
        def switch(*_a, **_k):
            window._open_project("P2")
            return str(target), "*.pdf"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", switch)
        window._export_offline_released("P1", "pdf")
        assert not target.exists()
        assert window.current_project_id == "P2"
        assert window._draft_report is None
    finally:
        window.close()


def test_online_release_buttons_disabled(tmp_path, qt_app):
    offline = seeded_window(tmp_path)
    service = offline._project_service
    offline.close()
    online = SolarCheckMainWindow(DeploymentMode.ONLINE, project_service=service)
    try:
        online._open_project("P1")
        assert not online._pages[ShellRoute.REPORT].findChild(
            QPushButton, "approve_report_release",
        )  # no draft in online mode
        assert not online._pages[ShellRoute.EXPORT].findChild(
            QPushButton, "export_report_released",
        ).isEnabled()
    finally:
        online.close()

def test_preview_pdf_is_real_and_only_scroll_to_bottom_marks_event(
    tmp_path, qt_app,
):
    pytest.importorskip("PySide6.QtPdf")
    pytest.importorskip("PySide6.QtPdfWidgets")
    from mcm_solarcheck.gui.report_pdf_preview import ReportPdfPreviewDialog
    from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP
    window = seeded_window(tmp_path)
    started = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
    try:
        window._prepare_report_draft("P1", "PDF-REVIEW", started)
        content = window._project_service.render_offline_draft_preview(
            "P1", "PDF-REVIEW", started, capabilities=OFFLINE_DESKTOP,
            expected_draft=window._draft_report,
        )
        assert content.startswith(b"%PDF")
        assert window._pages[ShellRoute.REPORT].findChild(
            QPushButton, "view_report_pdf",
        ).isEnabled()
        preview = ReportPdfPreviewDialog(content)
        try:
            assert not preview.reached_end
            preview.show()
            qt_app.processEvents()
            qt_app.processEvents()
            bar = preview.pdf_view.verticalScrollBar()
            assert preview._document.pageCount() >= 2
            assert bar.maximum() > 0
            assert not preview.reached_end
            bar.setValue(bar.maximum())
            qt_app.processEvents()
            assert preview.reached_end
        finally:
            preview.close()
    finally:
        window.close()


def test_unviewed_release_stays_false_in_admin_audit(
    tmp_path, qt_app,
):
    from mcm_solarcheck.services.authorized_grant_administration import GrantAdministrator
    from mcm_solarcheck.services.report_preview_audit_admin import AuthorizedReportPreviewAudit
    window = seeded_window(tmp_path)
    try:
        window._prepare_report_draft(
            "P1", "NO-PREVIEW", datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
        )
        page = window._pages[ShellRoute.REPORT]
        page.findChild(QLineEdit, "report_release_reviewer").setText("Expertin")
        page.findChild(QPushButton, "approve_report_release").click()
        admin = GrantAdministrator(
            "admin", True, frozenset({"report_release:audit_read"}),
        )
        entries = AuthorizedReportPreviewAudit(window._project_service.database).inspect(
            admin, "P1",
        )
        assert len(entries) == 1 and entries[0].reached_preview_end is False
        assert "reached_preview_end" not in page.findChild(
            QLabel, "report_release_status",
        ).text()
    finally:
        window.close()


def test_pdf_preview_scroll_captured_only_for_active_draft(
    tmp_path, qt_app, monkeypatch,
):
    pytest.importorskip("PySide6.QtPdf")
    pytest.importorskip("PySide6.QtPdfWidgets")
    from mcm_solarcheck.gui.report_pdf_preview import ReportPdfPreviewDialog
    from mcm_solarcheck.services.authorized_grant_administration import GrantAdministrator
    from mcm_solarcheck.services.report_preview_audit_admin import AuthorizedReportPreviewAudit
    window = seeded_window(tmp_path)
    started = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
    try:
        window._prepare_report_draft("P1", "WITH-PREVIEW", started)
        def preview_to_bottom(dialog):
            dialog.show()
            qt_app.processEvents()
            qt_app.processEvents()
            scrollbar = dialog.pdf_view.verticalScrollBar()
            assert scrollbar.maximum() > 0
            scrollbar.setValue(scrollbar.maximum())
            qt_app.processEvents()
            assert dialog.reached_end
            return 1
        monkeypatch.setattr(ReportPdfPreviewDialog, "exec", preview_to_bottom)
        window._pages[ShellRoute.REPORT].findChild(
            QPushButton, "view_report_pdf",
        ).click()
        assert window._report_end_seen
        page = window._pages[ShellRoute.REPORT]
        page.findChild(QLineEdit, "report_release_reviewer").setText("Expertin")
        page.findChild(QPushButton, "approve_report_release").click()
        admin = GrantAdministrator(
            "admin", True, frozenset({"report_release:audit_read"}),
        )
        events = AuthorizedReportPreviewAudit(window._project_service.database).inspect(
            admin, "P1",
        )
        assert len(events) == 1 and events[0].reached_preview_end is True
        window._open_project("P2")
        assert window._report_end_seen is False
    finally:
        window.close()


def test_project_switch_during_pdf_viewer_discards_scroll_event(
    tmp_path, qt_app, monkeypatch,
):
    pytest.importorskip("PySide6.QtPdf")
    pytest.importorskip("PySide6.QtPdfWidgets")
    from mcm_solarcheck.gui.report_pdf_preview import ReportPdfPreviewDialog
    window = seeded_window(tmp_path)
    try:
        window._prepare_report_draft(
            "P1", "STALE-VIEW", datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
        )
        def switch_during_modal(dialog):
            dialog.reached_end = True
            window._open_project("P2")
            return 1
        monkeypatch.setattr(ReportPdfPreviewDialog, "exec", switch_during_modal)
        window._preview_offline_report("P1")
        assert window.current_project_id == "P2"
        assert window._draft_report is None
        assert not window._report_end_seen
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
