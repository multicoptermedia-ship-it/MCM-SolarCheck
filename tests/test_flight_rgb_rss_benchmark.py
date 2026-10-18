"""Benchmark smoke tests: no customer images and no CI RSS threshold."""
import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_rss_benchmark import benchmark_jpeg_conversion


def test_isolated_rss_benchmark_reports_measured_bytes(tmp_path):
    source, target = tmp_path / "synthetic.jpg", tmp_path / "working.npy"
    assert cv2.imwrite(str(source), np.zeros((8, 8, 3), dtype=np.uint8))
    try:
        result = benchmark_jpeg_conversion(source, target)
    except RuntimeError as exc:
        pytest.skip(str(exc))
    assert result["measured"] is True
    assert result["isolated_subprocess"] is True
    assert result["peak_rss_bytes"] > 0
    assert np.load(target).shape == (8, 8, 3)
