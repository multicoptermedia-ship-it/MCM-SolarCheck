"""Global projective preview synthetic tests for RGB and thermal-like grayscale."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_projective_preview import compose_projective_visual_preview


@pytest.mark.parametrize("channels", [1, 3])
def test_projective_preview_renders_same_originals_once(channels):
    gray = np.random.default_rng(651 + channels).integers(0, 256, (256, 320), dtype=np.uint8)
    image = gray if channels == 1 else np.repeat(gray[:, :, None], 3, axis=2)
    result = compose_projective_visual_preview([image, image.copy(), image.copy()])
    assert result.image.shape == image.shape
    assert np.mean(np.abs(result.image.astype(float) - image.astype(float))) < 2.
    assert result.rms_corner_error_px < 1.
    assert result.preview_only and not result.metric_orthophoto_verified


def test_preview_canvas_limit_rejects_before_writing():
    frame = np.random.default_rng(654).integers(0, 256, (256, 320), dtype=np.uint8)
    with pytest.raises(ValueError, match="canvas limit"):
        compose_projective_visual_preview([frame] * 3, max_pixels=100)


def test_preview_mixed_channels_rejected():
    frame = np.random.default_rng(655).integers(0, 256, (256, 320), dtype=np.uint8)
    rgb = np.repeat(frame[:, :, None], 3, axis=2)
    with pytest.raises(ValueError, match="mixed image channel"):
        compose_projective_visual_preview([frame, rgb, frame])


def test_preview_rejects_nonredundant_graph_before_render(monkeypatch):
    from mcm_solarcheck.services import visual_projective_audit
    frame = np.random.default_rng(656).integers(0, 256, (256, 320), dtype=np.uint8)
    original = visual_projective_audit.estimate_visual_link

    def only_chain(first, second):
        # Distinguish identity-linked images by the unique first pixel.
        i, j = int(first[0, 0]), int(second[0, 0])
        if (i, j) == (1, 3):
            raise ValueError("no overlap")
        return original(first, second)

    frames = [frame.copy() for _ in range(3)]
    for idx, item in enumerate(frames):
        item[0, 0] = idx + 1
    monkeypatch.setattr(visual_projective_audit, "estimate_visual_link", only_chain)
    with pytest.raises(ValueError, match="redundant"):
        compose_projective_visual_preview(frames)
