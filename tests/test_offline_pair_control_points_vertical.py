"""Real Qt/SQLite vertical gate for explicit, expert-supplied controls.

No customer images, EXIF, GPS or original flight filenames are used.
"""
import json
import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from mcm_solarcheck.domain.models import ImageFrame, ImagePair, ThermalFrame
from mcm_solarcheck.gui.processing_page import make_processing_page
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.pairing.registration import ControlPoint, estimate_homography
from mcm_solarcheck.services.offline_pair_control_points import check_project_pair_control_points
from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def fixture_points():
    fit = [(30, 40), (130, 60), (240, 90), (80, 220),
           (330, 180), (500, 410), (50, 370), (570, 250)]
    hold = [(95, 85), (225, 175), (320, 340), (425, 260)]
    def mapped(p):
        x, y = p
        return [x, y, 100 + 5 * x, 80 + 5 * y]
    return [mapped(p) for p in fit], [mapped(p) for p in hold]


def quality():
    return ThermalQualityResult(
        ThermalQualityGrade.PASS, (),
        RawThermalStatistics(1, 10, 5., 5., 9., 10., 9),
    )


def populate(db, project="P1"):
    db.create_project(project, "Synthetic")
    db.save_image_frames(project, (
        ImageFrame("V1", Path("synthetic_V.JPG"), width=4000, height=3000),
    ))
    db.save_thermal_frame(project, ThermalFrame(
        "T1", Path("synthetic_T.JPG"),
        thermal_width=640, thermal_height=512, thermal_source="raw",
    ), quality())
    db.save_pairs(project, (ImagePair("PAIR1", "V1", "T1", 1.0, "sequence+time+position"),))


def write_payload(path, *, pair_id="PAIR1", fit=None, holdout=None):
    a, b = fixture_points()
    path.write_text(json.dumps({
        "schema": 1, "pair_id": pair_id,
        "fit_points": a if fit is None else fit,
        "holdout_points": b if holdout is None else holdout,
    }), encoding="utf-8")


def test_independent_holdout_good_but_unapproved(tmp_path):
    db = ProjectDatabase(tmp_path / "inspection.sqlite3")
    db.initialize()
    populate(db)
    src = tmp_path / "controls.json"
    write_payload(src)
    before = db.path.read_bytes()
    result = check_project_pair_control_points(db, "P1", src)
    assert result.status == "holdout_passed_unapproved"
    assert result.registration_approved is False
    assert result.report_approved is False
    assert result.fit_inliers >= 6
    assert result.holdout_points == 4
    assert result.holdout_rms_px < 0.01
    assert db.path.read_bytes() == before


def test_wrong_project_and_bad_reference_fail_closed(tmp_path):
    db = ProjectDatabase(tmp_path / "inspection.sqlite3")
    db.initialize()
    populate(db, "P1")
    db.create_project("P2", "Other")
    src = tmp_path / "points.json"
    write_payload(src)
    with pytest.raises(ValueError, match="Stored pair"):
        check_project_pair_control_points(db, "P2", src)
    write_payload(src, pair_id="UNKNOWN")
    with pytest.raises(ValueError, match="Stored pair"):
        check_project_pair_control_points(db, "P1", src)


def test_refuses_bad_holdout_duplicate_fit_and_out_of_bounds(tmp_path):
    db = ProjectDatabase(tmp_path / "inspection.sqlite3")
    db.initialize()
    populate(db)
    src = tmp_path / "points.json"
    fit, hold = fixture_points()
    for changed_fit, changed_hold, expected in (
        (fit, [p[:2] + [p[2] + 100, p[3]] for p in hold],
         "reprojection_error_too_high"),
        (fit[:-1] + [fit[0]], hold, "duplicate_fit_points"),
        (fit, hold[:-1] + [fit[0]], "fit_holdout_overlap"),
        (fit, hold[:-1] + [[999, 100, 200, 300]],
         "control_points_out_of_bounds"),
    ):
        write_payload(src, fit=changed_fit, holdout=changed_hold)
        outcome = check_project_pair_control_points(db, "P1", src)
        assert outcome.status == "refused"
        assert outcome.reason == expected


def test_rejects_nonfinite_and_large_json(tmp_path):
    db = ProjectDatabase(tmp_path / "inspection.sqlite3")
    db.initialize()
    populate(db)
    src = tmp_path / "points.json"
    fit, hold = fixture_points()
    write_payload(src, fit=fit[:-1] + [[float("nan"), 1, 1, 1]])
    with pytest.raises(ValueError, match="finite"):
        check_project_pair_control_points(db, "P1", src)
    src.write_text(" " * 130000, encoding="utf-8")
    with pytest.raises(ValueError, match="small"):
        check_project_pair_control_points(db, "P1", src)


def test_legacy_grid_extrapolation_and_strict_manual_limits():
    fit, hold = fixture_points()
    points = tuple(ControlPoint(*v) for v in fit)
    check = tuple(ControlPoint(*v) for v in hold)
    fit_outside = (replace(points[0], thermal_x=-1., rgb_x=95.),) + points[1:]
    free = estimate_homography(fit_outside, check)
    assert free.quality.reason != "control_points_out_of_bounds"
    strict = estimate_homography(fit_outside, check, require_in_bounds=True)
    assert strict.quality.reason == "control_points_out_of_bounds"


def test_expert_panel_is_opt_in_and_does_not_store_registration(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "offline.sqlite3")
    try:
        populate(window._project_service.database)
        src = tmp_path / "valid.json"
        write_payload(src)
        window._open_project("P1")
        page = window._pages[ShellRoute.PROCESSING]
        toggle = page.findChild(QPushButton, "processing_registration_toggle")
        action = page.findChild(QPushButton, "processing_check_registration_button")
        assert toggle is not None and action.isEnabled()
        assert page.findChild(QLabel, "processing_registration_result") is None
        window._check_pair_control_points(str(src))
        page = window._pages[ShellRoute.PROCESSING]
        result = page.findChild(QLabel, "processing_registration_result")
        assert "nicht freigegebener Kandidat" in result.text()
        assert "synthetic" not in result.text()
        assert window._project_service.import_summary("P1").image_pairs == 1
        window._open_project("P2") if any(
            p.project_id == "P2" for p in window._project_service.projects()
        ) else None
    finally:
        window.close()
