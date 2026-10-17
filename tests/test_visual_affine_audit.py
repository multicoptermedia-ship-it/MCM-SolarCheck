"""Modality-shared affine graph entrypoint smoke tests."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_affine_audit import audit_visual_affine_graph


def test_identical_grayscale_frames_have_identity_anchor():
    frame = np.random.default_rng(231).integers(0, 256, (256, 320), dtype=np.uint8)
    result = audit_visual_affine_graph([frame, frame.copy(), frame.copy()])
    for h in result.transforms_to_anchor:
        assert np.allclose(h, np.eye(3), atol=.01)
    assert result.preview_only and not result.metric_orthophoto_verified


def test_identical_rgb_frames_use_same_entrypoint():
    gray = np.random.default_rng(232).integers(0, 256, (256, 320), dtype=np.uint8)
    frame = np.repeat(gray[:, :, None], 3, axis=2)
    result = audit_visual_affine_graph([frame, frame.copy(), frame.copy()])
    assert len(result.transforms_to_anchor) == 3


def test_invalid_frame_count_fails():
    frame = np.zeros((256, 320), dtype=np.uint8)
    with pytest.raises(ValueError, match="3-8"):
        audit_visual_affine_graph([frame, frame])
