"""Interrupted export inspection must be read-only and conservative."""
import json

import cv2
import numpy as np

import pytest

from mcm_solarcheck.services.flight_rgb_export_recovery import inspect_rgb_export_directory


def test_inspector_reports_orphans_and_staging_without_changes(tmp_path):
    assert cv2.imwrite(str(tmp_path / "segment_0000.png"), np.zeros((4, 4, 3), np.uint8))
    (tmp_path / ".rgb-preview-123.tmp").write_bytes(b"private")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = inspect_rgb_export_directory(tmp_path)
    assert result["segments"][0]["status"] == "missing_partner"
    assert result["segments"][0]["missing"] == ["json"]
    assert result["staging_files"] == [".rgb-preview-123.tmp"]
    assert result["summary"] == "absent"
    assert result["read_only"] is True
    assert result["requires_manual_review"] is True
    assert result["issues"] == 2
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_inspector_detects_invalid_quality(tmp_path):
    assert cv2.imwrite(str(tmp_path / "segment_0001.png"), np.zeros((4, 4, 3), np.uint8))
    (tmp_path / "segment_0001.json").write_text(json.dumps({
        "processing_kind": "nonmetric_rgb_segment_preview",
        "metric_orthophoto_verified": True,
    }), encoding="utf-8")
    assert inspect_rgb_export_directory(tmp_path)["segments"][0]["status"] == "invalid_quality"


def test_inspector_rejects_symlink(tmp_path):
    (tmp_path / "source").write_text("customer")
    (tmp_path / "segment_0000.png").symlink_to(tmp_path / "source")
    with pytest.raises(ValueError, match="symlink"):
        inspect_rgb_export_directory(tmp_path)


def test_inspector_accepts_valid_pair_and_summary(tmp_path):
    assert cv2.imwrite(str(tmp_path / "segment_0000.png"), np.zeros((4, 4, 3), np.uint8))
    (tmp_path / "segment_0000.json").write_text(json.dumps({
        "processing_kind": "nonmetric_rgb_segment_preview",
        "metric_orthophoto_verified": False,
    }), encoding="utf-8")
    (tmp_path / "segments_summary.json").write_text(json.dumps({
        "processing_kind": "nonmetric_rgb_flight_segment_previews",
        "segments": [{"index": 0, "status": "exported",
                      "image": "segment_0000.png", "quality": "segment_0000.json"}],
    }), encoding="utf-8")
    result = inspect_rgb_export_directory(tmp_path)
    assert result["segments"][0]["status"] == "paired"
    assert result["summary"] == "present"
    assert result["issues"] == 0
    assert result["requires_manual_review"] is False


def test_inspector_reports_corrupt_png_without_modifying_it(tmp_path):
    image = tmp_path / "segment_0002.png"
    image.write_bytes(b"not a png")
    (tmp_path / "segment_0002.json").write_text(json.dumps({
        "processing_kind": "nonmetric_rgb_segment_preview",
        "metric_orthophoto_verified": False,
    }), encoding="utf-8")
    result = inspect_rgb_export_directory(tmp_path)
    assert result["segments"][0]["status"] == "invalid_png"
    assert result["requires_manual_review"] is True
    assert image.read_bytes() == b"not a png"


def test_inspector_reports_summary_mismatch(tmp_path):
    (tmp_path / "segments_summary.json").write_text(json.dumps({
        "processing_kind": "nonmetric_rgb_flight_segment_previews",
        "segments": [{"index": 4, "status": "exported",
                      "image": "segment_0004.png", "quality": "segment_0004.json"}],
    }), encoding="utf-8")
    result = inspect_rgb_export_directory(tmp_path)
    assert result["summary"] == "present"
    assert result["summary_mismatches"] == ["exported_segment_0004"]
    assert result["requires_manual_review"] is True
