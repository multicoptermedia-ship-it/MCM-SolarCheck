"""Large-camera RGB regression: 20 MP originals into bounded tile-readable arrays.

One synthetic full-resolution JPEG exercises native-pixel conversion without
claiming a streaming JPEG decoder, DJI flight test or measured peak RAM.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pytest

from mcm_solarcheck.services.flight_rgb_batch_conversion import convert_jpeg_batch
from mcm_solarcheck.services.flight_rgb_jpeg_conversion import convert_jpeg_to_rgb_array
from mcm_solarcheck.services.flight_rgb_resource_plan import estimate_rgb_conversion_resources
from mcm_solarcheck.services.flight_rgb_tile_source import RGBArrayTileSource
from mcm_solarcheck.services.flight_rgb_tile_plan import RGBTile


WIDTH, HEIGHT = 5000, 4000  # 20,000,000 true pixels


def test_twenty_megapixel_original_reaches_native_rgb_tile_source(tmp_path):
    original = tmp_path / "synthetic-20MP.jpg"
    destination = tmp_path / "synthetic-20MP.npy"
    Image.new("RGB", (WIDTH, HEIGHT), (180, 40, 20)).save(original, "JPEG")
    unchanged = original.read_bytes()

    result = convert_jpeg_to_rgb_array(original, destination)
    assert (result["width"], result["height"]) == (WIDTH, HEIGHT)
    assert result["decoded_pixels"] == 20_000_000
    assert result["source_modified"] is False
    assert result["jpeg_region_decoding"] is False
    assert original.read_bytes() == unchanged

    tiles = RGBArrayTileSource(destination)
    assert (tiles.width, tiles.height) == (WIDTH, HEIGHT)
    near_edge = tiles.read_tile(RGBTile(WIDTH - 16, HEIGHT - 8, 16, 8))
    assert near_edge.shape == (8, 16, 3)
    assert near_edge[:, :, 0].mean() > 160
    assert near_edge[:, :, 1].mean() < 70
    assert destination.stat().st_size >= WIDTH * HEIGHT * 3


def test_twenty_megapixel_resource_estimate_is_not_measured_memory():
    plan = estimate_rgb_conversion_resources([(WIDTH, HEIGHT)])
    assert plan["frame_count"] == 1
    assert plan["estimated_working_disk_bytes"] == 60_000_000 + 4096
    assert plan["estimated_peak_ram_bytes"] == 300_000_000
    assert plan["peak_rss_measured"] is False
    assert plan["estimate_only"] is True


def test_twenty_four_megapixel_header_output_budget_fails_before_cv2_decode(
    tmp_path, monkeypatch,
):
    src, dest = tmp_path / "small.jpg", tmp_path / "working.npy"
    assert cv2.imwrite(str(src), np.zeros((8, 8, 3), np.uint8))
    monkeypatch.setattr(
        "mcm_solarcheck.services.flight_rgb_jpeg_conversion.jpeg_dimensions",
        lambda path: (6000, 4000),
    )
    def do_not_decode(*args, **kwargs):
        raise AssertionError("must reject insufficient output bytes before decode")
    monkeypatch.setattr(
        "mcm_solarcheck.services.flight_rgb_jpeg_conversion.cv2.imdecode",
        do_not_decode,
    )
    with pytest.raises(ValueError, match="output byte budget"):
        convert_jpeg_to_rgb_array(src, dest, max_output_bytes=70_000_000)
    assert not dest.exists()


def test_future_camera_larger_than_default_remains_explicitly_bounded(
    tmp_path, monkeypatch,
):
    src, dest = tmp_path / "small.jpg", tmp_path / "working.npy"
    assert cv2.imwrite(str(src), np.zeros((8, 8, 3), np.uint8))
    monkeypatch.setattr(
        "mcm_solarcheck.services.flight_rgb_jpeg_conversion.jpeg_dimensions",
        lambda path: (7000, 4000),
    )
    def do_not_decode(*args, **kwargs):
        raise AssertionError("oversized camera must fail before allocating image")
    monkeypatch.setattr(
        "mcm_solarcheck.services.flight_rgb_jpeg_conversion.cv2.imdecode",
        do_not_decode,
    )
    with pytest.raises(ValueError, match="pixel budget before decode"):
        convert_jpeg_to_rgb_array(src, dest)
    assert not dest.exists()


def test_batch_preflight_rejects_large_source_when_total_quota_too_small(
    tmp_path, monkeypatch,
):
    src = tmp_path / "synthetic.jpg"
    output = tmp_path / "derived"
    output.mkdir()
    assert cv2.imwrite(str(src), np.zeros((8, 8, 3), np.uint8))
    monkeypatch.setattr(
        "mcm_solarcheck.services.flight_rgb_batch_conversion.jpeg_dimensions",
        lambda path: (WIDTH, HEIGHT),
    )
    with pytest.raises(ValueError, match="batch disk quota"):
        convert_jpeg_batch([src], output, max_total_disk_bytes=60_000_000)
    assert list(output.iterdir()) == []
    assert src.exists()


def test_batch_preflight_accepts_twenty_megapixel_budget_before_converter(
    tmp_path, monkeypatch,
):
    src = tmp_path / "synthetic.jpg"
    output = tmp_path / "derived"
    output.mkdir()
    assert cv2.imwrite(str(src), np.zeros((8, 8, 3), np.uint8))
    monkeypatch.setattr(
        "mcm_solarcheck.services.flight_rgb_batch_conversion.jpeg_dimensions",
        lambda path: (WIDTH, HEIGHT),
    )
    call = []
    def fake_converter(source, destination, **kwargs):
        call.append((source, destination, kwargs))
        return {}
    monkeypatch.setattr(
        "mcm_solarcheck.services.flight_rgb_batch_conversion.convert_jpeg_to_rgb_array",
        fake_converter,
    )
    result = convert_jpeg_batch(
        [src], output, max_total_disk_bytes=60_000_000 + 4096,
    )
    assert result["completed_outputs"] == ["synthetic.npy"]
    assert result["resource_plan"]["estimated_working_disk_bytes"] == 60_004_096
    assert len(call) == 1
    assert call[0][2]["max_pixels"] == 24_000_000
    assert call[0][2]["max_output_bytes"] == 80_000_000
    assert src.exists()


def test_invalid_output_cap_cannot_be_overridden_by_high_pixel_limit(tmp_path):
    original = tmp_path / "small.jpg"
    target = tmp_path / "derived.npy"
    assert cv2.imwrite(str(original), np.zeros((24, 24, 3), np.uint8))
    with pytest.raises(ValueError, match="output byte budget"):
        convert_jpeg_to_rgb_array(
            original, target, max_pixels=50_000_000, max_output_bytes=100,
        )
    assert not target.exists()
