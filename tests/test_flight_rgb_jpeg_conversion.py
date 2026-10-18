"""Regression tests for conservative JPEG working-array conversion."""
import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_jpeg_conversion import convert_jpeg_to_rgb_array
from mcm_solarcheck.services.flight_rgb_tile_source import RGBArrayTileSource
from mcm_solarcheck.services.flight_rgb_tile_plan import RGBTile


def test_jpeg_conversion_preserves_source_and_reads_tiles(tmp_path):
    source, target = tmp_path / "capture.jpg", tmp_path / "working.npy"
    bgr = np.zeros((8, 12, 3), dtype=np.uint8)
    bgr[:, :, 2] = 240
    assert cv2.imwrite(str(source), bgr)
    original = source.read_bytes()
    result = convert_jpeg_to_rgb_array(source, target, max_pixels=96)
    assert result["decoded_pixels"] == 96
    assert result["jpeg_region_decoding"] is False
    assert source.read_bytes() == original
    reader = RGBArrayTileSource(target, max_tile_pixels=16)
    tile = reader.read_tile(RGBTile(0, 0, 4, 4))
    assert tile.shape == (4, 4, 3)
    assert tile[:, :, 0].mean() > 200


def test_jpeg_conversion_never_overwrites_destination(tmp_path):
    source, target = tmp_path / "capture.jpg", tmp_path / "working.npy"
    assert cv2.imwrite(str(source), np.zeros((4, 4, 3), dtype=np.uint8))
    target.write_bytes(b"customer data")
    with pytest.raises(ValueError):
        convert_jpeg_to_rgb_array(source, target)
    assert target.read_bytes() == b"customer data"


def test_jpeg_conversion_enforces_pixel_budget(tmp_path):
    source, target = tmp_path / "capture.jpg", tmp_path / "working.npy"
    assert cv2.imwrite(str(source), np.zeros((4, 4, 3), dtype=np.uint8))
    with pytest.raises(ValueError, match="pixel budget"):
        convert_jpeg_to_rgb_array(source, target, max_pixels=15)
    assert not target.exists()


def test_jpeg_conversion_rejects_output_disk_budget(tmp_path):
    source, target = tmp_path / "capture.jpg", tmp_path / "working.npy"
    assert cv2.imwrite(str(source), np.zeros((4, 4, 3), dtype=np.uint8))
    with pytest.raises(ValueError, match="output byte budget"):
        convert_jpeg_to_rgb_array(source, target, max_output_bytes=32)
    assert not target.exists()


def test_jpeg_conversion_rejects_insufficient_free_space(tmp_path, monkeypatch):
    source, target = tmp_path / "capture.jpg", tmp_path / "working.npy"
    assert cv2.imwrite(str(source), np.zeros((4, 4, 3), dtype=np.uint8))
    monkeypatch.setattr(
        "mcm_solarcheck.services.flight_rgb_jpeg_conversion.shutil.disk_usage",
        lambda path: type("Usage", (), {"free": 0})(),
    )
    with pytest.raises(ValueError, match="disk space"):
        convert_jpeg_to_rgb_array(source, target)
    assert not target.exists()
