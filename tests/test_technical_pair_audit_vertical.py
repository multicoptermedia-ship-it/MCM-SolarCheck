"""Synthetic acquisition-pair audit: SQLite -> service -> offline GUI.

No real DJI files, EXIF, original image bytes or coordinates from customers.
"""
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel

from mcm_solarcheck.domain.models import ImageFrame, ImagePair, Position, ThermalFrame
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.storage.queries import InspectionQueries
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def _quality():
    return ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5.0, 5.0, 9.0, 10.0, 9),
    )


def seed_pair(db, project, number, *, metadata=True, saved=True,
              record_confidence=None, record_method=None):
    stamp = datetime(2026, 10, 22, 10, tzinfo=timezone.utc) if metadata else None
    position = Position(51.0, 7.0) if metadata else None
    source = "DJI_20261022100000_" + number
    rgb = ImageFrame(
        "V-" + number, Path(source + "_V.JPG"), timestamp_utc=stamp,
        position=position,
    )
    thermal = ThermalFrame(
        "T-" + number, Path(source + "_T.JPG"), timestamp_utc=stamp,
        position=position, thermal_width=640, thermal_height=512, thermal_source="raw",
    )
    db.save_image_frames(project, (rgb,))
    db.save_thermal_frame(project, thermal, _quality())
    if saved:
        db.save_pairs(project, (
            ImagePair(
                "PAIR-" + number, rgb.frame_id, thermal.frame_id,
                record_confidence if record_confidence is not None
                else (1.0 if metadata else 0.65),
                record_method if record_method is not None
                else ("sequence+time+position" if metadata else "sequence"),
            ),
        ))


def test_aggregate_support_and_cross_project_scope(tmp_path):
    db = ProjectDatabase(tmp_path / "pilot.sqlite3")
    db.initialize()
    db.create_project("PILOT", "Synthetic pilot")
    db.create_project("OTHER", "Private separate project")
    seed_pair(db, "PILOT", "0128")
    seed_pair(db, "PILOT", "0129", metadata=False)
    seed_pair(db, "OTHER", "0130")
    # Original pilot also contains non-paired thermal observations.
    db.save_thermal_frame(
        "PILOT", ThermalFrame(
            "T-0131", Path("DJI_20261022100000_0131_T.JPG"),
            thermal_width=640, thermal_height=512, thermal_source="raw",
        ), _quality(),
    )
    audit = InspectionQueries(db).technical_pair_audit("PILOT")
    assert audit.pairs_recorded == 2
    assert audit.supported_by_current_rules == 1
    assert audit.require_review == 1
    assert audit.with_matching_sequence == 2
    assert audit.with_close_time == 1
    assert audit.with_close_position == 1
    assert audit.unmatched_rgb == 0
    assert audit.unmatched_thermal == 1
    assert InspectionQueries(db).technical_pair_audit("OTHER").supported_by_current_rules == 1
    assert not hasattr(audit, "source_file")
    with pytest.raises(KeyError):
        InspectionQueries(db).technical_pair_audit("MISSING")


def test_empty_and_unstored_pair_remain_unverified(tmp_path):
    db = ProjectDatabase(tmp_path / "empty.sqlite3")
    db.initialize()
    db.create_project("EMPTY", "Empty")
    audit = InspectionQueries(db).technical_pair_audit("EMPTY")
    assert audit.pairs_recorded == audit.require_review == 0
    seed_pair(db, "EMPTY", "0180", saved=False)
    audit = InspectionQueries(db).technical_pair_audit("EMPTY")
    assert audit.pairs_recorded == 0
    assert audit.unmatched_rgb == audit.unmatched_thermal == 1


def test_stale_score_or_duplicate_pair_cannot_be_approved_by_read_only_audit(tmp_path):
    db = ProjectDatabase(tmp_path / "stale.sqlite3")
    db.initialize()
    db.create_project("PILOT", "Pilot")
    seed_pair(db, "PILOT", "0144", record_confidence=0.75)
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO image_pairs "
            "(project_id,pair_id,rgb_frame_id,thermal_frame_id,confidence,method) "
            "VALUES (?,?,?,?,?,?)",
            ("PILOT", "PAIR-DUPLICATE", "V-0144", "T-0144", 1.0,
             "sequence+time+position"),
        )
    audit = InspectionQueries(db).technical_pair_audit("PILOT")
    assert audit.pairs_recorded == 2
    assert audit.supported_by_current_rules == 0
    assert audit.require_review == 2


def test_offline_gui_shows_only_aggregate_evidence(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "desktop.sqlite3")
    try:
        service = window._project_service
        service.create_project("PILOT", "Synthetic")
        seed_pair(service.database, "PILOT", "0128")
        window._open_project("PILOT")
        overview = service.processing_overview("PILOT")
        assert overview.pair_audit.supported_by_current_rules == 1
        processing_page = window._pages[ShellRoute.PROCESSING]
        label = processing_page.findChild(QLabel, "processing_pair_evidence")
        assert label is not None
        assert "Gespeicherte Bildpaare: 1" in label.text()
        assert "nach aktueller" in label.text().lower() or "Zuordnungsregel" in label.text()
        assert "DJI_2026" not in label.text()
        import_page = window._pages[ShellRoute.IMPORT]
        import_label = import_page.findChild(QLabel, "import_pair_evidence_explanation")
        assert import_label is not None
        assert "1 von 1" in import_label.text()
        assert "keine pixelgenaue" in import_label.text().lower()
    finally:
        window.close()
