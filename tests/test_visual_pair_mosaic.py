"""Synthetic visual mosaics; no customer photographs."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_pair_mosaic import compose_visual_pair


def test_identical_textured_rgb_frames_form_non_metric_preview():
    rng = np.random.default_rng(7)
    image = rng.integers(0, 256, size=(280, 360, 3), dtype=np.uint8)
    result = compose_visual_pair(image, image)
    assert result.inliers >= 12
    assert result.image.ndim == 3
    assert result.image.shape[2] == 3
    assert result.preview_only
    assert result.metric_orthophoto_verified is False


def test_blank_frames_rejected():
    blank = np.zeros((256, 256, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="features"):
        compose_visual_pair(blank, blank)


def test_canvas_budget_enforced():
    rng = np.random.default_rng(7)
    image = rng.integers(0, 256, size=(280, 360, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="canvas"):
        compose_visual_pair(image, image, max_pixels=100)


def test_invalid_input_rejected():
    with pytest.raises(ValueError, match="uint8 RGB"):
        compose_visual_pair(np.zeros((256, 256), dtype=np.uint8), np.zeros((256, 256, 3), dtype=np.uint8))
