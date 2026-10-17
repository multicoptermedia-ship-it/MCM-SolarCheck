"""Synthetic RGB/thermal-display adapter and shared registration tests."""
import numpy as np
import pytest

from mcm_solarcheck.services.registration_image import registration_gray
from mcm_solarcheck.services.visual_frame_registration import estimate_visual_link


def test_rgb_and_grayscale_use_same_registration_geometry():
    gray = np.random.default_rng(95).integers(0, 256, (256, 320), dtype=np.uint8)
    rgb = np.repeat(gray[:, :, None], 3, axis=2)
    assert np.array_equal(registration_gray(rgb), gray)
    assert np.array_equal(registration_gray(gray), gray)
    h, count = estimate_visual_link(gray, gray.copy())
    assert count >= 12
    assert np.allclose(h / h[2, 2], np.eye(3), atol=0.05)


def test_three_channel_thermal_palette_is_only_visual_input():
    image = np.random.default_rng(96).integers(0, 256, (256, 320, 3), dtype=np.uint8)
    h, count = estimate_visual_link(image, image.copy())
    assert count >= 12
    assert np.isfinite(h).all()


@pytest.mark.parametrize("bad", [
    np.zeros((256, 320), dtype=np.float32),
    np.zeros((100, 320), dtype=np.uint8),
    np.zeros((256, 320, 2), dtype=np.uint8),
])
def test_invalid_visual_inputs_fail_closed(bad):
    with pytest.raises(ValueError):
        registration_gray(bad)
