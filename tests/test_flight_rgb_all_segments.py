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


def test_long_segment_sampling_is_explicit_and_bounded(tmp_path, monkeypatch):
    from mcm_solarcheck.services import flight_rgb_folder_preview as preview
    source = tmp_path / "DJI_20260725154421_0000_V.PNG"
    assert cv2.imwrite(str(source), np.full((160, 160, 3), 90, np.uint8))
    keys = [f"frame_{i}" for i in range(10)]
    monkeypatch.setattr(preview, "scan_flight",
                        lambda folder: ([(key, source, None) for key in keys], None))
    registration = {"nonmetric_geometry": {"segments": [
        {"frames": {key: np.eye(3).tolist() for key in keys}}
    ]}}
    with pytest.raises(ValueError, match="frame limit"):
        preview.export_flight_rgb_segment(
            tmp_path, registration, 0, tmp_path / "strict.png", tmp_path / "strict.json",
            max_frames=3)
    metadata = preview.export_flight_rgb_segment(
        tmp_path, registration, 0, tmp_path / "sample.png", tmp_path / "sample.json",
        max_frames=3, sample_long_segments=True)
    assert metadata["preview_incomplete"] is True
    assert metadata["source_frame_count"] == 10
    assert metadata["preview_frame_count"] == 3
    assert metadata["preview_frame_keys"] == [keys[0], keys[4], keys[9]]
    assert source.exists()


def test_full_flight_reports_sampled_long_segment(tmp_path, monkeypatch):
    from mcm_solarcheck.services import flight_rgb_folder_preview as preview
    source = tmp_path / "DJI_20260725154421_0000_V.PNG"
    assert cv2.imwrite(str(source), np.full((160, 160, 3), 70, np.uint8))
    keys = [f"frame_{i}" for i in range(9)]
    monkeypatch.setattr(preview, "scan_flight",
                        lambda folder: ([(key, source, None) for key in keys], None))
    registration = {"nonmetric_geometry": {"segments": [
        {"frames": {key: np.eye(3).tolist() for key in keys}}
    ]}}
    output = tmp_path / "output"
    output.mkdir()
    result = save_all_flight_rgb_segments(tmp_path, registration, output)
    assert result["exported"] == 1
    assert result["sampled_previews"] == 1
    assert result["segments"][0]["preview_incomplete"] is True
    assert result["segments"][0]["preview_frame_count"] == 8
    quality = json.loads((output / "segment_0000.json").read_text())
    assert quality["source_frame_count"] == 9
    assert quality["preview_frame_count"] == 8
    assert quality["metric_orthophoto_verified"] is False
    assert json.loads((output / "segments_summary.json").read_text()) == result


def test_quality_json_is_complete_on_first_publication(tmp_path, monkeypatch):
    from mcm_solarcheck.services import flight_rgb_folder_preview as preview
    source = tmp_path / "DJI_20260725154421_0000_V.PNG"
    assert cv2.imwrite(str(source), np.full((160, 160, 3), 70, np.uint8))
    monkeypatch.setattr(preview, "scan_flight",
                        lambda folder: ([("one", source, None)], None))
    registration = {"nonmetric_geometry": {"segments": [
        {"frames": {"one": np.eye(3).tolist()}}
    ]}}
    png, quality = tmp_path / "result.png", tmp_path / "result.json"
    result = preview.export_flight_rgb_segment(tmp_path, registration, 0, png, quality)
    assert json.loads(quality.read_text()) == result
    assert result["preview_frame_keys"] == ["one"]
    assert not list(tmp_path.glob(".rgb-preview-*"))


def test_quality_publish_failure_cleans_new_png(tmp_path, monkeypatch):
    from mcm_solarcheck.services import flight_rgb_segment_export as exporter
    frames = {"one": np.full((160, 160, 3), 70, np.uint8)}
    segment = {"frames": {"one": np.eye(3).tolist()}}
    png = tmp_path / "preview.png"
    quality = tmp_path / "preview.json"
    original_open = __import__("pathlib").Path.open

    def fail_quality(path, mode="r", *args, **kwargs):
        if path == quality and mode == "xb":
            raise OSError("simulated quality write failure")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(__import__("pathlib").Path, "open", fail_quality)
    with pytest.raises(OSError, match="simulated"):
        exporter.save_rgb_segment_preview(segment, frames, png, quality)
    assert not png.exists()
    assert not quality.exists()
    assert not list(tmp_path.glob(".rgb-preview-*"))
