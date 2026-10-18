"""Synthetic tests for nonmetric bounded RGB canvas planning and rendering."""
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_canvas_plan import plan_rgb_canvas
from mcm_solarcheck.services.flight_rgb_segment_render import render_rgb_segment


def test_translated_frames_blend_and_extend_canvas():
    identity = np.eye(3).tolist()
    moved = [[1, 0, 5], [0, 1, 0], [0, 0, 1]]
    segment = {"frames": {"a": identity, "b": moved}}
    a = np.full((10, 10, 3), 60, dtype=np.uint8)
    b = np.full((10, 10, 3), 160, dtype=np.uint8)
    image, quality = render_rgb_segment(segment, {"a": a, "b": b})
    assert image.shape == (10, 15, 3)
    assert image[5, 2, 0] == 160
    assert image[5, 7, 0] == 110
    assert image[5, 12, 0] == 60
    assert quality["nonmetric"] is True
    assert quality["native_resolution"] is False


def test_canvas_rejects_excessive_pixel_count():
    segment = {"frames": {"a": np.eye(3).tolist()}}
    with pytest.raises(ValueError, match="pixel limit"):
        plan_rgb_canvas(segment, {"a": (100, 100)}, max_pixels=99)


def test_canvas_rejects_missing_dimensions():
    segment = {"frames": {"a": np.eye(3).tolist()}}
    with pytest.raises(ValueError, match="missing RGB dimensions"):
        plan_rgb_canvas(segment, {})
