"""Regression tests for sequential RGB segment flight export."""
import json

import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_all_segments import (
    export_all_flight_rgb_segments, save_all_flight_rgb_segments,
)


def _registration(keys):
    return {"nonmetric_geometry": {"segments": [
        {"frames": {key: np.eye(3).tolist()}} for key in keys
    ]}}


def test_all_segments_export_and_sources_unchanged(tmp_path):
    source = tmp_path / "DJI_20260725154421_0000_V.PNG"
    assert cv2.imwrite(str(source), np.full((160, 160, 3), 80, np.uint8))
    original = source.read_bytes()
    output = tmp_path / "results"
    output.mkdir()
    result = save_all_flight_rgb_segments(
        tmp_path, _registration(["20260725154421_0000"]), output
    )
    assert (result["exported"], result["failed"]) == (1, 0)
    assert (output / "segment_0000.png").exists()
    assert (output / "segment_0000.json").exists()
    assert json.loads((output / "segments_summary.json").read_text()) == result
    assert source.read_bytes() == original


def test_failed_segment_does_not_block_next(tmp_path):
    source = tmp_path / "DJI_20260725154421_0000_V.PNG"
    assert cv2.imwrite(str(source), np.full((160, 160, 3), 90, np.uint8))
    output = tmp_path / "results"
    output.mkdir()
    result = export_all_flight_rgb_segments(
        tmp_path, _registration(["missing", "20260725154421_0000"]), output
    )
    assert result["failed"] == 1
    assert result["exported"] == 1
    assert result["segments"][0]["status"] == "failed"
    assert (output / "segment_0001.png").exists()


def test_empty_output_directory_required(tmp_path):
    output = tmp_path / "results"
    output.mkdir()
    (output / "existing.txt").write_text("preserve")
    with pytest.raises(ValueError, match="empty regular"):
        export_all_flight_rgb_segments(tmp_path, _registration([]), output)
    assert (output / "existing.txt").read_text() == "preserve"


def test_cancel_before_next_segment(tmp_path):
    output = tmp_path / "results"
    output.mkdir()
    result = export_all_flight_rgb_segments(
        tmp_path, _registration(["missing", "missing2"]), output,
        should_cancel=lambda: True,
    )
    assert result["processed"] == 0
    assert result["cancelled"] is True
