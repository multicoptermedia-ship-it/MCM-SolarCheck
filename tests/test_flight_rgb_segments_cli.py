"""End-to-end checks for the offline full-flight RGB preview export CLI."""
import json

import cv2
import numpy as np

from mcm_solarcheck.services.flight_rgb_segments_cli import main


def test_cli_exports_two_segments_and_reports_progress(tmp_path, capsys):
    originals = {}
    keys = []
    for index in range(2):
        key = f"20260725154421_{index:04d}"
        image = tmp_path / f"DJI_{key}_V.PNG"
        assert cv2.imwrite(str(image), np.full((160, 160, 3), 60 + index * 50, np.uint8))
        originals[image] = image.read_bytes()
        keys.append(key)
    registration = {"nonmetric_geometry": {"segments": [
        {"frames": {key: np.eye(3).tolist()}} for key in keys
    ]}}
    source_json = tmp_path / "registration.json"
    source_json.write_text(json.dumps(registration), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    assert main([str(tmp_path), str(source_json), str(output)]) == 0
    summary = json.loads((output / "segments_summary.json").read_text(encoding="utf-8"))
    assert summary["segment_count"] == summary["exported"] == 2
    assert summary["metric_orthophoto_verified"] is False
    assert "2/2: segment 1 exported" in capsys.readouterr().out
    for image, original in originals.items():
        assert image.read_bytes() == original


def test_cli_reports_segment_failure_with_nonzero_exit(tmp_path):
    registration = {"nonmetric_geometry": {"segments": [
        {"frames": {"missing": np.eye(3).tolist()}}
    ]}}
    source_json = tmp_path / "registration.json"
    source_json.write_text(json.dumps(registration), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    assert main([str(tmp_path), str(source_json), str(output)]) == 1
    summary = json.loads((output / "segments_summary.json").read_text(encoding="utf-8"))
    assert summary["failed"] == 1
    assert summary["segments"][0]["status"] == "failed"
