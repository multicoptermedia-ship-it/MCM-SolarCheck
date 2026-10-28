"""Synthetic full-project SQLite -> multiple original JPEGs -> verified-plane tiles.

No real images, customer positions, uploads or database writes are used.
"""
import hashlib
import json
import sqlite3
import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.rgb_project_roof_vertical import (
    RGBProjectRoofCancelled, create_project_rgb_roof_tiles,
)
from mcm_solarcheck.services.rgb_project_roof_cli import main


def _inputs(tmp_path, count=3):
    photos = tmp_path / "originals"
    photos.mkdir()
    database = tmp_path / "test.sqlite"
    destination = tmp_path / "tiles"
    destination.mkdir()
    frames, controls, image_files = [], [], []
    with sqlite3.connect(database) as sql:
        sql.execute("CREATE TABLE projects(project_id TEXT)")
        sql.execute("CREATE TABLE image_frames(project_id TEXT, frame_id TEXT, source_file TEXT, width INTEGER, height INTEGER)")
        sql.execute("INSERT INTO projects VALUES (?)", ("SC-TEST",))
        for i in range(count):
            identifier = f"rgb-{i}"
            photo = photos / f"DJI_20250825121642_{136+i:04d}_V.JPG"
            assert cv2.imwrite(str(photo), np.full((128, 128, 3), 100 + 10*i, np.uint8))
            image_files.append(photo)
            sql.execute("INSERT INTO image_frames VALUES (?,?,?,?,?)", ("SC-TEST", identifier, str(photo), 128, 128))
            frames.append({
                "frame_id": identifier,
                "imported_pose_degrees": {"yaw_deg": 0, "pitch_deg": -90, "roll_deg": 0},
                "intrinsics": {"fx": 40, "fy": 40, "cx": 64, "cy": 64},
                "camera_to_enu": [[1,0,0],[0,-1,0],[0,0,-1]],
                "center_enu_m": [0,0,10], "calibration_provenance": "synthetic camera",
                "rotation_provenance": "synthetic ENU", "survey_provenance": "synthetic roof",
                "lens_undistortion_verified": True, "reference_frames_verified": True,
                "distortion_coefficients": [0,0,0,0,0],
            })
            for j, (east, north) in enumerate(((-1,-1),(-1,1),(1,-1),(1,1))):
                controls.append({
                    "frame_id": identifier, "control_id": f"held-out-{j}",
                    "undistorted_pixel_xy": [64 + 4*east, 64 - 4*north],
                    "surveyed_point_enu_m": [east, north, 0],
                })
    package = {
        "schema": "mcm.rgb_roof_external_geometry.v1",
        "plane": {"point_enu_m": [0,0,0], "normal_enu": [0,0,1]},
        "grid": {
            "u_min_m": -1, "v_min_m": -1, "metres_per_pixel": 0.1,
            "width": 20, "height": 20, "tile_side_px": 16,
        },
        "frames": frames, "controls": controls,
        "control_survey_provenance": "independent synthetic test",
        "allowed_surface_error_m": .1,
    }
    return database, destination, image_files, package


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_complete_rgb_project_renders_bounded_tiles_without_touching_originals(tmp_path):
    database, target, photos, package = _inputs(tmp_path)
    before = [_digest(path) for path in (database, *photos)]
    ticks = []
    result = create_project_rgb_roof_tiles(
        database, "SC-TEST", package, target,
        on_progress=lambda done,total: ticks.append((done,total)),
    )
    assert result.source_count == 3
    assert result.tile_count == 4
    assert ticks == [(1,3), (2,3), (3,3)]
    assert result.coverage_fraction == pytest.approx(1.)
    assert not result.orthophoto_verified
    data = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert data["source_count"] == 3
    assert data["held_out_control_count"] == 12
    assert data["whole_imported_rgb_series_processed"] is True
    assert data["rgb_orthophoto_verified"] is False
    assert data["controls_provenance_independently_authenticated"] is False
    assert data["pv_module_detection_performed"] is False
    assert len(list(target.glob("rgb-roof-r*-c*.png"))) == 8
    assert str(photos[0]) not in result.manifest_path.read_text(encoding="utf-8")
    assert [_digest(path) for path in (database, *photos)] == before


def test_all_imported_rgb_frames_need_independent_geometry(tmp_path):
    database, target, _, package = _inputs(tmp_path)
    package["frames"].pop()
    with pytest.raises(ValueError, match="every imported RGB"):
        create_project_rgb_roof_tiles(database, "SC-TEST", package, target)
    assert not list(target.iterdir())


def test_wrong_held_out_control_blocks_raster_before_writes(tmp_path):
    database, target, _, package = _inputs(tmp_path)
    package["controls"][0]["undistorted_pixel_xy"][0] += 8
    with pytest.raises(ValueError, match="residual exceeds"):
        create_project_rgb_roof_tiles(database, "SC-TEST", package, target)
    assert not list(target.iterdir())


def test_cancelled_full_series_cannot_publish_partial_tiles(tmp_path):
    database, target, _, package = _inputs(tmp_path)
    cancellation = {"value": False}
    with pytest.raises(RGBProjectRoofCancelled):
        create_project_rgb_roof_tiles(
            database, "SC-TEST", package, target,
            should_cancel=lambda: cancellation["value"],
            on_progress=lambda done,total: cancellation.update(value=True),
        )
    assert not list(target.iterdir())


def test_unknown_project_and_missing_survey_are_closed(tmp_path):
    database, target, _, package = _inputs(tmp_path)
    with pytest.raises(ValueError, match="selected project"):
        create_project_rgb_roof_tiles(database, "UNKNOWN", package, target)
    with pytest.raises(ValueError, match="external camera"):
        create_project_rgb_roof_tiles(database, "SC-TEST", {}, target)
    assert not list(target.iterdir())


def test_cli_uses_real_project_and_declared_geometry_only(tmp_path, capsys):
    database, target, _, package = _inputs(tmp_path)
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(package), encoding="utf-8")
    assert main([
        "--database", str(database), "--project-id", "SC-TEST",
        "--geometry-json", str(geometry), "--output-dir", str(target),
    ]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["rgb_frames"] == 3
    assert info["tiles"] == 4
    assert info["orthophoto_verified"] is False
