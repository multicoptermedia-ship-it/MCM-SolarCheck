"""Flight-wide collision preflight is fail-closed and read-only."""
import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_integrity_scan import scan_rgb_integrity


def test_colliding_jpeg_stems_rejected_before_progress(tmp_path):
    source = tmp_path / "images"
    output = tmp_path / "working"
    source.mkdir()
    output.mkdir()
    for name in ("same.jpg", "same.jpeg"):
        assert cv2.imwrite(str(source / name), np.zeros((4, 5, 3), dtype=np.uint8))
    progress = []
    with pytest.raises(ValueError, match="colliding"):
        scan_rgb_integrity(source, output, on_progress=lambda *args: progress.append(args))
    assert progress == []
    assert list(output.iterdir()) == []


def test_scan_refuses_symlinked_jpeg(tmp_path):
    source = tmp_path / "images"
    output = tmp_path / "working"
    source.mkdir()
    output.mkdir()
    original = tmp_path / "original.jpg"
    assert cv2.imwrite(str(original), np.zeros((4, 5, 3), dtype=np.uint8))
    (source / "linked.jpg").symlink_to(original)
    with pytest.raises(ValueError, match="regular JPEG"):
        scan_rgb_integrity(source, output)
