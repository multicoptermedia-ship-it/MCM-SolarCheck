"""Synthetic Windows-pilot regression: visible controls and explicit stored pairing.

No DJI customer originals, GPS records or imported project data are checked in.
"""
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QComboBox, QDialogButtonBox, QLabel, QPushButton

from mcm_solarcheck.domain.models import ImageFrame, Position, ThermalFrame
from mcm_solarcheck.domain.project_profile import ProjectProfile
from mcm_solarcheck.gui.import_page import make_import_page
from mcm_solarcheck.gui.project_page import EditProjectProfileDialog, NewProjectDialog
from mcm_solarcheck.gui.theme import APP_STYLE_SHEET
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_navigation_and_standard_buttons_have_non_hover_contrast():
    assert "QWidget#workflow_navigation QPushButton {" in APP_STYLE_SHEET
    assert "QWidget#workflow_navigation QPushButton:disabled" in APP_STYLE_SHEET
    assert "QPushButton:disabled" in APP_STYLE_SHEET
    assert "color: #d3dad5" in APP_STYLE_SHEET


def test_new_project_timezone_is_a_real_choice(qt_app):
    dialog = NewProjectDialog()
    try:
        choice = dialog.findChild(QComboBox, "new_project_site_timezone_choice")
        assert choice is not None
        assert not choice.isEditable()
        assert choice.findData("Europe/Berlin") >= 0
        ok = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
        for field, value in (
            ("project_id", "P1"), ("name", "Pilot"),
            ("customer_name", "Synthetic"), ("site_name", "Anlage"),
            ("site_street", "Musterweg 1"), ("site_postal_code", "12345"),
            ("site_city", "Teststadt"), ("inspector", "Pruefer"),
        ):
            getattr(dialog, field).setText(value)
        assert not ok.isEnabled()
        choice.setCurrentIndex(choice.findData("Europe/Berlin"))
        assert dialog.profile().site_timezone == "Europe/Berlin"
        assert ok.isEnabled()
    finally:
        dialog.close()


def test_edit_timezone_choice_keeps_project_metadata(qt_app):
    profile = ProjectProfile("Kunde", "Anlage", "Weg 1", "12345", "Ort", "Pruefer",
                             site_timezone="Europe/Berlin", order_reference="ALTE-REF")
    dialog = EditProjectProfileDialog(profile)
    try:
        choice = dialog.findChild(QComboBox, "edit_profile_site_timezone_choice")
        assert choice.currentData() == "Europe/Berlin"
        choice.setCurrentIndex(choice.findData("Europe/Zurich"))
        assert dialog.profile().site_timezone == "Europe/Zurich"
        assert dialog.profile().order_reference == "ALTE-REF"
        choice.setCurrentIndex(0)
        assert dialog.profile().site_timezone is None
    finally:
        dialog.close()


def test_import_primary_actions_and_advanced_panel(qt_app):
    calls = []
    summary = SimpleNamespace(rgb_frames=33, thermal_frames=160, image_pairs=0)
    page = make_import_page(
        current_project_id="PILOT", import_summary=summary,
        on_reconcile_pairs=lambda: calls.append("reconcile"),
    )
    try:
        assert page.findChild(QLabel, "import_pair_review_hint") is not None
        action = page.findChild(QPushButton, "import_reconcile_pairs_button")
        assert action.isEnabled()
        action.click()
        assert calls == ["reconcile"]
        panel = page.findChild(QPushButton, "import_advanced_toggle")
        advanced = page.findChild(QPushButton, "import_original_zips_button")
        assert panel.isCheckable()
        assert advanced is not None
        assert page.findChild(QLabel, "import_summary").text() == (
            "33 RGB · 160 Thermal · 0 Paare"
        )
        assert page.findChild(QPushButton, "import_original_files_button") is not None
        panel.click()
        assert panel.isChecked()
    finally:
        page.close()


def _quality():
    return ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )


def _seed(db, project, number, *, matched=True):
    capture = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
    location = Position(51.0, 7.0)
    rgb = ImageFrame(
        "V-" + number, Path("DJI_20261022120000_" + number + "_V.JPG"),
        timestamp_utc=capture if matched else None,
        position=location if matched else None,
    )
    thermal = ThermalFrame(
        "T-" + number, Path("DJI_20261022120000_" + number + "_T.JPG"),
        timestamp_utc=capture if matched else None,
        position=location if matched else None,
        thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    db.save_image_frames(project, (rgb,))
    db.save_thermal_frame(project, thermal, _quality())


def test_explicit_reconciliation_is_idempotent_and_project_scoped(tmp_path):
    db = ProjectDatabase(tmp_path / "pilot.sqlite3")
    db.initialize()
    db.create_project("P1", "Erster synthetischer Import")
    db.create_project("P2", "Unberuehrtes Projekt")
    _seed(db, "P1", "0128")
    _seed(db, "P1", "0129", matched=False)
    _seed(db, "P2", "0130")
    service = ProjectApplicationService(db)

    assert service.import_summary("P1").image_pairs == 0
    assert service.reconcile_imported_pairs("P1") == 1
    assert service.reconcile_imported_pairs("P1") == 0
    assert service.import_summary("P1").image_pairs == 1
    assert service.import_summary("P2").image_pairs == 0

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT confidence,method FROM image_pairs WHERE project_id=?",
            ("P1",),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["confidence"] >= 0.70
        assert "sequence" in rows[0]["method"]
    with pytest.raises(KeyError):
        service.reconcile_imported_pairs("UNKNOWN")


def test_reconciliation_never_accepts_sequence_alone(tmp_path):
    db = ProjectDatabase(tmp_path / "only-sequence.sqlite3")
    db.initialize()
    db.create_project("P1", "Unpaired test")
    _seed(db, "P1", "0142", matched=False)
    service = ProjectApplicationService(db)
    assert service.reconcile_imported_pairs("P1") == 0
    assert service.import_summary("P1").image_pairs == 0
    with pytest.raises(ValueError, match="conservative"):
        db.reconcile_persisted_image_pairs("P1", minimum_confidence=0.65)
