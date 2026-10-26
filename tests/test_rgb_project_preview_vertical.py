"""End-to-end offline project -> ORIGINAL RGB -> unverified PNG + JSON test.

All test photos and the SQLite database are synthesized in tmp_path.
No real private drone files, external network, camera calibration or roof claims.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.rgb_project_preview_cli import main
from mcm_solarcheck.services.rgb_project_preview_vertical import (
    create_project_rgb_preview,
)


@pytest.fixture
def pilot_inputs(tmp_path: Path):
    db_path = tmp_path / "test.sqlite3"
    originals = tmp_path / "private-originals"
    originals.mkdir()
    destination = tmp_path / "preview"
    destination.mkdir()

    # Deterministic textured ORIGINAL RGB images; no fake roof metadata.
    rng = np.random.default_rng(2026)
    image = rng.integers(0, 256, size=(768, 1024, 3), dtype=np.uint8)
    paths = []
    for index in (136, 137):
        path = originals / f"DJI_20250825121642_{index:04d}_V.JPG"
        assert cv2.imwrite(str(path), image)
        paths.append(path)

    with sqlite3.connect(db_path) as db:
        db.executescript("""
            CREATE TABLE projects(project_id TEXT PRIMARY KEY, name TEXT);
            CREATE TABLE image_frames(
                project_id TEXT, frame_id TEXT, source_file TEXT,
                width INTEGER, height INTEGER, timestamp_utc TEXT
            );
        """)
        db.execute("INSERT INTO projects VALUES (?, ?)", ("P1", "Testprojekt"))
        db.executemany("INSERT INTO image_frames VALUES (?,?,?,?,?,?)", [
            ("P1", "f136", str(paths[0]), 1024, 768, "2025-08-25T12:16:42"),
            ("P1", "f137", str(paths[1]), 1024, 768, "2025-08-25T12:16:43"),
        ])
    return db_path, tuple(paths), destination


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_real_vertical_rgb_preview_writes_only_bounded_diagnostic(pilot_inputs):
    db, paths, target = pilot_inputs
    before = {path: digest(path) for path in (db, *paths)}
    result = create_project_rgb_preview(
        db, "P1", "0136", "0137", target, max_side=700,
        max_canvas_pixels=2_000_000,
    )
    assert result.png_path == target / "rgb-stitch-preview.png"
    assert result.manifest_path == target / "rgb-stitch-preview.json"
    assert result.inliers >= 20
    assert result.status == "unverified_nonmetric_rgb_preview"
    assert not result.metric_orthophoto_verified
    assert set(target.iterdir()) == {result.png_path, result.manifest_path}
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert payload["verified_orthomosaic"] is False
    assert payload["status"] == "unverified_preview"
    assert payload["source_names"] == [p.name for p in paths]
    assert payload["frame_count"] == 2
    png = cv2.imread(str(result.png_path), cv2.IMREAD_COLOR)
    assert png is not None and png.shape[0] * png.shape[1] <= 2_000_000
    assert all(digest(path) == sha for path, sha in before.items())


def test_cli_one_command_path_uses_same_read_only_pipeline(pilot_inputs, capsys):
    db, _, target = pilot_inputs
    assert main([
        "--database", str(db), "--project-id", "P1",
        "--first", "0136", "--second", "0137",
        "--output-dir", str(target),
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["metric_orthophoto_verified"] is False
    assert output["primary_rgb_frames"] == ["0136", "0137"]
    assert Path(output["image"]).is_file()


@pytest.mark.parametrize("first,second", [
    ("0136", "0138"), ("136", "0137"), ("0137", "0136"),
])
def test_invalid_or_nonconsecutive_rgb_pair_is_rejected(pilot_inputs, first, second):
    db, _, target = pilot_inputs
    with pytest.raises(ValueError, match="consecutive"):
        create_project_rgb_preview(db, "P1", first, second, target)
    assert not list(target.iterdir())


def test_unknown_project_or_output_inside_originals_fails_closed(pilot_inputs):
    db, paths, target = pilot_inputs
    with pytest.raises(ValueError, match="project"):
        create_project_rgb_preview(db, "unknown", "0136", "0137", target)
    inner = paths[0].parent / "output"
    inner.mkdir()
    with pytest.raises(ValueError, match="inside original-photo"):
        create_project_rgb_preview(db, "P1", "0136", "0137", inner)


def test_mismatched_declared_primary_rgb_dimensions_stop_before_outputs(pilot_inputs):
    db, _, target = pilot_inputs
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE image_frames SET width=960 WHERE frame_id='f136'")
    with pytest.raises(ValueError, match="primary frame dimensions"):
        create_project_rgb_preview(db, "P1", "0136", "0137", target)
    assert not list(target.iterdir())


def test_existing_output_file_cannot_be_overwritten(pilot_inputs):
    db, paths, target = pilot_inputs
    (target / "rgb-stitch-preview.png").write_bytes(b"PREEXISTING")
    with pytest.raises(ValueError, match="empty"):
        create_project_rgb_preview(db, "P1", "0136", "0137", target)
    assert (target / "rgb-stitch-preview.png").read_bytes() == b"PREEXISTING"
