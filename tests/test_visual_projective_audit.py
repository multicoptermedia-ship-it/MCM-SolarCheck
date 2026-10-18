"""Synthetic RGB and thermal-like grayscale projective graph entrypoint tests."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_projective_audit import audit_visual_projective_graph


@pytest.mark.parametrize("channels", [1, 3])
def test_shared_registration_projective_graph_identity(channels):
    gray = np.random.default_rng(230 + channels).integers(0, 256, (256, 320), dtype=np.uint8)
    frame = gray if channels == 1 else np.repeat(gray[:, :, None], 3, axis=2)
    result = audit_visual_projective_graph([frame, frame.copy(), frame.copy()])
    assert result.rms_corner_error_px < 1.
    assert len(result.transforms_to_anchor) == 3
    assert result.preview_only and not result.metric_orthophoto_verified


def test_blank_frames_rejected_as_disconnected():
    frame = np.zeros((256, 320), dtype=np.uint8)
    with pytest.raises(ValueError, match="link count"):
        audit_visual_projective_graph([frame, frame.copy(), frame.copy()])
