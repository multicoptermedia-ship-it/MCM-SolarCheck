"""Geometry direction and DJI-folder preview integration regression tests."""
import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_canvas_plan import plan_rgb_canvas
from mcm_solarcheck.services.flight_rgb_segment_render import render_rgb_segment
from mcm_solarcheck.services.flight_rgb_folder_preview import export_flight_rgb_segment


def test_forward_link_translation_is_inverted_for_anchor_canvas():
    segment = {"frames": {
        "a": np.eye(3).tolist(),
        "b": [[1, 0, 5], [0, 1, 0], [0, 0, 1]],
    }}
    plan = plan_rgb_canvas(segment, {"a": (10, 10), "b": (10, 10)})
    assert plan["origin"] == [-5, 0]
    assert plan["width"] == 15
    image, _ = render_rgb_segment(segment, {
        "a": np.full((10, 10, 3), 60, dtype=np.uint8),
        "b": np.full((10, 10, 3), 160, dtype=np.uint8),
    })
    assert image[5, 2, 0] == 160
    assert image[5, 7, 0] == 110
    assert image[5, 12, 0] == 60


def test_folder_export_uses_dji_rgb_without_touching_source(tmp_path):
    image = np.full((160, 160, 3), 80, dtype=np.uint8)
    source = tmp_path / "DJI_20260725154421_0000_V.PNG"
    assert cv2.imwrite(str(source), image)
    original = source.read_bytes()
    registration = {"nonmetric_geometry": {"segments": [
        {"frames": {"20260725154421_0000": np.eye(3).tolist()}}
    ]}}
    png = tmp_path / "preview.png"
    quality = tmp_path / "quality.json"
    result = export_flight_rgb_segment(tmp_path, registration, 0, png, quality)
    assert result["nonmetric"] is True
    assert png.is_file() and quality.is_file()
    assert source.read_bytes() == original
    with pytest.raises(ValueError, match="new PNG"):
        export_flight_rgb_segment(tmp_path, registration, 0, png, quality)
