"""Offline Qt master-data editing: user action -> SQLite -> report draft gates.

Only synthetic project data is used. The dialog has no online write capability.
"""
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLabel, QLineEdit, QPushButton

from mcm_solarcheck.domain.models import Finding, PVModule, ThermalFrame
from mcm_solarcheck.domain.project_profile import ProjectProfile
from mcm_solarcheck.gui.project_page import EditProjectProfileDialog
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


STAMP = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def sample_profile():
    return ProjectProfile(
        "Fiktiver Kunde", "Solarpark Nord", "Musterweg 1", "12345",
        "Musterstadt", "Pruefer A",
        customer_contact="Kontakt erhalten",
        customer_email="synthetisch@example.invalid",
        order_reference="4711", site_timezone="Europe/Berlin",
    )


def seed_window(tmp_path):
    window = build_offline_window(tmp_path / "inspection.sqlite3")
    service = window._project_service
    original = sample_profile()
    service.create_project_with_profile("P1", "Projekt Nord", original)
    service.create_project_with_profile(
        "P2", "Projekt Sued", replace(original, site_name="Sued"),
    )
    frame = ThermalFrame(
        frame_id="T1", source_file=Path("synthetic.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    quality = ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )
    service.database.save_thermal_frame("P1", frame, quality)
    service.database.save_modules(
        "P1", (PVModule("M1", "T1", ((0, 0), (2, 0), (2, 2))),),
    )
    service.database.save_findings("P1", (
        Finding("F1", "T1", 2, 3, module_id="M1", reviewer_status="confirmed"),
    ))
    window._open_project("P1")
    return window


def project_button(window):
    return window._pages[ShellRoute.PROJECT].findChild(
        QPushButton, "edit_project_profile_button",
    )


def profile_status(window):
    return window._pages[ShellRoute.PROJECT].findChild(
        QLabel, "project_profile_edit_status",
    )


def test_edit_dialog_requires_real_change_and_preserves_optional_fields(qt_app):
    profile = sample_profile()
    dialog = EditProjectProfileDialog(profile)
    try:
        ok = dialog.findChild(QDialogButtonBox).button(
            QDialogButtonBox.StandardButton.Ok,
        )
        assert dialog.windowTitle() == "Projektstammdaten bearbeiten"
        assert not ok.isEnabled()
        site = dialog.findChild(QLineEdit, "edit_profile_site_name")
        assert site.text() == "Solarpark Nord"
        site.setText("  Solarpark Mitte  ")
        assert ok.isEnabled()
        changed = dialog.profile()
        assert changed.site_name == "Solarpark Mitte"
        assert changed.customer_email == profile.customer_email
        assert changed.customer_contact == profile.customer_contact
        assert changed.order_reference == profile.order_reference
        dialog.findChild(QLineEdit, "edit_profile_site_timezone").setText(
            "Invalid/TimeZone/Example",
        )
        assert not ok.isEnabled()
        dialog.findChild(QLineEdit, "edit_profile_site_timezone").setText("")
        assert ok.isEnabled()
        assert dialog.profile().site_timezone is None
        site.setText("")
        assert not ok.isEnabled()
    finally:
        dialog.close()


def test_edit_active_project_updates_sqlite_and_invalidates_prepared_draft(
    qt_app, tmp_path, monkeypatch,
):
    window = seed_window(tmp_path)
    service = window._project_service
    old = service.project_profile("P1")
    untouched = service.project_profile("P2")
    try:
        window._prepare_report_draft("P1", "ENTWURF-1", STAMP)
        assert window._draft_report is not None
        assert project_button(window).isEnabled()
        assert "P1" in window._pages[ShellRoute.PROJECT].findChild(
            QLabel, "project_profile_context",
        ).text()

        def accept_edited(self):
            assert self.fields["site_name"].text() == "Solarpark Nord"
            assert self.fields["inspector"].text() == "Pruefer A"
            self.fields["site_name"].setText("Solarpark Mitte")
            self.fields["inspector"].setText("Pruefer B")
            assert self._ok_button.isEnabled()
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(EditProjectProfileDialog, "exec", accept_edited)
        project_button(window).click()
        updated = service.project_profile("P1")
        assert updated.site_name == "Solarpark Mitte"
        assert updated.inspector == "Pruefer B"
        assert updated.customer_email == old.customer_email
        assert updated.order_reference == old.order_reference
        assert service.project_profile("P2") == untouched
        assert window._draft_report is None
        assert window._draft_request is None
        assert "gespeichert" in profile_status(window).text()
        assert window._pages[ShellRoute.REPORT].findChild(
            QLabel, "report_draft_preview",
        ) is None
        assert not window._pages[ShellRoute.EXPORT].findChild(
            QPushButton, "export_report_draft",
        ).isEnabled()

        window._prepare_report_draft("P1", "ENTWURF-NEU", STAMP)
        assert window._draft_report.site_name == "Solarpark Mitte"
    finally:
        window.close()


def test_cancel_and_noop_leave_draft_untouched(qt_app, tmp_path, monkeypatch):
    window = seed_window(tmp_path)
    try:
        window._prepare_report_draft("P1", "DRAFT", STAMP)
        original_draft = window._draft_report
        original = window._project_service.project_profile("P1")
        monkeypatch.setattr(
            EditProjectProfileDialog, "exec",
            lambda self: QDialog.DialogCode.Rejected,
        )
        project_button(window).click()
        assert window._draft_report is original_draft
        assert window._project_service.project_profile("P1") == original
        window._update_project_profile("P1", original, original)
        assert window._draft_report is original_draft
        assert "Keine Änderung" in profile_status(window).text()
    finally:
        window.close()


def test_stale_dialog_cannot_overwrite_concurrent_change(
    qt_app, tmp_path, monkeypatch,
):
    window = seed_window(tmp_path)
    original = window._project_service.project_profile("P1")
    newer = replace(original, site_city="Neustadt")
    try:
        window._prepare_report_draft("P1", "DRAFT", STAMP)

        def external_update_during_dialog(self):
            window._project_service.save_project_profile("P1", newer)
            self.fields["site_city"].setText("Altdaten")
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(
            EditProjectProfileDialog, "exec", external_update_during_dialog,
        )
        project_button(window).click()
        assert window._project_service.project_profile("P1") == newer
        assert window._draft_report is None
        assert window._draft_request is None
        status = profile_status(window).text()
        assert "nicht gespeichert" in status
        assert "Neustadt" not in status
        assert "Altdaten" not in status
    finally:
        window.close()


def test_modal_project_switch_prevents_cross_project_profile_edit(
    qt_app, tmp_path, monkeypatch,
):
    window = seed_window(tmp_path)
    service = window._project_service
    before_first = service.project_profile("P1")
    before_second = service.project_profile("P2")
    try:
        def change_project_during_dialog(self):
            window._open_project("P2")
            self.fields["site_name"].setText("Falsches Zielprojekt")
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(
            EditProjectProfileDialog, "exec", change_project_during_dialog,
        )
        project_button(window).click()
        assert window.current_project_id == "P2"
        assert service.project_profile("P1") == before_first
        assert service.project_profile("P2") == before_second
        assert profile_status(window) is None
        assert "P2" in window._pages[ShellRoute.PROJECT].findChild(
            QLabel, "project_profile_context",
        ).text()
    finally:
        window.close()


def test_online_window_never_exposes_local_project_profile_editor(qt_app, tmp_path):
    offline = seed_window(tmp_path)
    service = offline._project_service
    original = service.project_profile("P1")
    offline.close()
    online = SolarCheckMainWindow(DeploymentMode.ONLINE, project_service=service)
    try:
        online._open_project("P1")
        assert not project_button(online).isEnabled()
        online._update_project_profile(
            "P1", original, replace(original, inspector="Unzulässig"),
        )
        assert service.project_profile("P1") == original
        assert profile_status(online) is None
    finally:
        online.close()


def test_legacy_project_can_receive_missing_master_data(qt_app, tmp_path, monkeypatch):
    window = build_offline_window(tmp_path / "legacy.sqlite3")
    service = window._project_service
    try:
        service.create_project("LEGACY", "Alter Import")
        window._open_project("LEGACY")
        assert service.project_profile("LEGACY") is None

        def enter_required_values(self):
            assert not self._ok_button.isEnabled()
            for key, value in (
                ("customer_name", "Kunde"), ("site_name", "Anlage"),
                ("site_street", "Straße 1"), ("site_postal_code", "12345"),
                ("site_city", "Musterstadt"), ("inspector", "Pruefer"),
                ("site_timezone", "Europe/Berlin"),
            ):
                self.fields[key].setText(value)
            assert self._ok_button.isEnabled()
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(EditProjectProfileDialog, "exec", enter_required_values)
        project_button(window).click()
        profile = service.project_profile("LEGACY")
        assert profile.site_name == "Anlage"
        assert profile.site_timezone == "Europe/Berlin"
        assert profile.order_reference is None
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
