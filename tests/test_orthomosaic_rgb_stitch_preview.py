"""RGB stitching preview: real pixels, conservative failures, no ortho claim."""
import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.orthomosaic_rgb_stitch_preview import stitch_rgb_preview


def test_overlapping_rgb_images_produce_unverified_preview(tmp_path):
    rng = np.random.default_rng(42)
    base = rng.integers(0, 256, (480, 560, 3), dtype=np.uint8)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    assert cv2.imwrite(str(first), base)
    assert cv2.imwrite(str(second), base)
    result = stitch_rgb_preview(first, second)
    assert result.image.ndim == 3
    assert result.image.shape[1] >= 560
    assert result.inliers >= 20
    assert result.verified_orthomosaic is False


def test_stitch_preview_rejects_invalid_limits(tmp_path):
    with pytest.raises(ValueError, match="resource limits"):
        stitch_rgb_preview(tmp_path / "a", tmp_path / "b", max_side=100)


def test_stitch_preview_rejects_missing_images(tmp_path):
    with pytest.raises(ValueError):
        stitch_rgb_preview(tmp_path / "a.png", tmp_path / "b.png")
