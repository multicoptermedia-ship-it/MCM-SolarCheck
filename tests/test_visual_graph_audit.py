"""Shared RGB and grayscale graph diagnostic tests."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_graph_audit import audit_visual_translation_graph


def test_identical_rgb_frames_form_consistent_complete_graph():
    frame = np.random.default_rng(112).integers(0, 256, (256, 320, 3), dtype=np.uint8)
    result = audit_visual_translation_graph([frame, frame.copy(), frame.copy()])
    assert result.accepted_edges == ((0, 1), (0, 2), (1, 2))
    assert not result.missing_edges
    assert result.rms_residual_px < 1.
    assert result.preview_only and not result.metric_orthophoto_verified


def test_grayscale_visual_frames_use_same_graph_code():
    frame = np.random.default_rng(113).integers(0, 256, (256, 320), dtype=np.uint8)
    result = audit_visual_translation_graph([frame, frame.copy(), frame.copy()])
    assert len(result.accepted_edges) == 3
    assert result.rms_residual_px < 1.


def test_unconnected_graph_fails_closed():
    frame = np.random.default_rng(114).integers(0, 256, (256, 320), dtype=np.uint8)
    with pytest.raises(ValueError, match="disconnected"):
        audit_visual_translation_graph([frame, frame.copy(), np.zeros_like(frame)])


def test_invalid_count_rejected():
    frame = np.zeros((256, 320), dtype=np.uint8)
    with pytest.raises(ValueError, match="3-8"):
        audit_visual_translation_graph([frame, frame])
