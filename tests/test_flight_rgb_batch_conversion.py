"""Sequential batch preflight and no-clobber tests."""
import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_batch_conversion import convert_jpeg_batch


def _jpeg(path):
    assert cv2.imwrite(str(path), np.zeros((4, 5, 3), dtype=np.uint8))
    return path


def test_sequential_batch_outputs(tmp_path):
    inputs = [_jpeg(tmp_path / "a.jpg"), _jpeg(tmp_path / "b.jpg")]
    output = tmp_path / "derived"
    output.mkdir()
    result = convert_jpeg_batch(inputs, output, max_total_disk_bytes=10000)
    assert result["completed_outputs"] == ["a.npy", "b.npy"]
    assert result["sequential"] and not result["atomic_batch"]
    assert np.load(output / "a.npy").shape == (4, 5, 3)
    assert all(p.exists() for p in inputs)


def test_batch_quota_rejected_before_any_output(tmp_path):
    inputs = [_jpeg(tmp_path / "a.jpg"), _jpeg(tmp_path / "b.jpg")]
    output = tmp_path / "derived"
    output.mkdir()
    with pytest.raises(ValueError, match="quota"):
        convert_jpeg_batch(inputs, output, max_total_disk_bytes=100)
    assert list(output.iterdir()) == []


def test_batch_rejects_collisions_before_writes(tmp_path):
    inputs = [_jpeg(tmp_path / "a.jpg"), _jpeg(tmp_path / "a.jpeg")]
    output = tmp_path / "derived"
    output.mkdir()
    with pytest.raises(ValueError, match="colliding"):
        convert_jpeg_batch(inputs, output, max_total_disk_bytes=10000)
    assert list(output.iterdir()) == []
