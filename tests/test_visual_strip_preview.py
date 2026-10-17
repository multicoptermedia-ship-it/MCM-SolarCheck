"""Deterministic synthetic checks for experimental RGB strip chaining."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_strip_preview import compose_visual_strip


def test_three_matching_frames_generate_nonmetric_strip():
    image = np.random.default_rng(27).integers(0, 256, (256, 320, 3), dtype=np.uint8)
    result = compose_visual_strip([image, image.copy(), image.copy()])
    assert len(result.pair_inliers) == 2
    assert min(result.pair_inliers) >= 12
    assert result.image.shape[2] == 3
    assert result.preview_only is True
    assert result.metric_orthophoto_verified is False


def test_blank_transition_aborts_entire_strip():
    image = np.random.default_rng(27).integers(0, 256, (256, 320, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="features"):
        compose_visual_strip([image, image.copy(), np.zeros_like(image)])


def test_strip_rejects_excessive_frame_count():
    image = np.zeros((256, 320, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="requires"):
        compose_visual_strip([image] * 5)


def test_strip_rejects_excessive_canvas():
    image = np.random.default_rng(27).integers(0, 256, (256, 320, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="canvas"):
        compose_visual_strip([image, image], max_pixels=100)
