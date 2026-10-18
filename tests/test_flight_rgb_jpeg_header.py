"""JPEG header preflight regression tests."""
import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_jpeg_header import jpeg_dimensions


def test_baseline_jpeg_dimensions_without_decode(tmp_path):
    path = tmp_path / "capture.jpg"
    assert cv2.imwrite(str(path), np.zeros((11, 17, 3), dtype=np.uint8))
    assert jpeg_dimensions(path) == (17, 11)


@pytest.mark.parametrize("payload", [
    b"", b"not jpeg", b"\xff\xd8\xff\xd9",
    b"\xff\xd8\xff\xe0\x00\x00",
])
def test_reject_malformed_headers(tmp_path, payload):
    path = tmp_path / "bad.jpg"
    path.write_bytes(payload)
    with pytest.raises(ValueError):
        jpeg_dimensions(path)


def test_reject_header_over_budget(tmp_path):
    path = tmp_path / "capture.jpg"
    assert cv2.imwrite(str(path), np.zeros((8, 8, 3), dtype=np.uint8))
    with pytest.raises(ValueError):
        jpeg_dimensions(path, max_header_bytes=16)
