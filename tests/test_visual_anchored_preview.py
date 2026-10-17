"""Synthetic regression tests for common-anchor non-metric RGB previews."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_anchored_preview import compose_anchored_visual_preview


def test_identical_three_frames_are_anchored_without_resampling_drift():
    rgb = np.random.default_rng(46).integers(0, 256, (256, 320, 3), dtype=np.uint8)
    result = compose_anchored_visual_preview([rgb, rgb.copy(), rgb.copy()])
    assert len(result.pair_inliers) == 2
    assert min(result.pair_inliers) >= 12
    assert result.image.shape[2] == 3
    assert result.preview_only and not result.metric_orthophoto_verified


def test_weak_link_aborts_entire_preview():
    rgb = np.random.default_rng(46).integers(0, 256, (256, 320, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="features"):
        compose_anchored_visual_preview([rgb, rgb.copy(), np.zeros_like(rgb)])


def test_canvas_limit_is_enforced():
    rgb = np.random.default_rng(46).integers(0, 256, (256, 320, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="canvas"):
        compose_anchored_visual_preview([rgb, rgb], max_pixels=100)


def test_invalid_frame_is_rejected():
    rgb = np.zeros((256, 320, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="invalid RGB"):
        compose_anchored_visual_preview([rgb, rgb[:, :, 0]])
