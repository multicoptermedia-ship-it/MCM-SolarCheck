"""Native-pixel RGB segment regression tests, synthetic imagery only."""
import numpy as np
import pytest
from PIL import Image

from mcm_solarcheck.services.flight_native_rgb import compose_native_rgb_segment


def _inputs(tmp_path):
    pixels = np.random.default_rng(1029).integers(
        0, 256, (260, 340, 3), dtype=np.uint8
    )
    files = []
    for i in range(3):
        path = tmp_path / f"original_{i}.png"
        Image.fromarray(pixels).save(path)
        files.append(path)
    return files


def test_native_output_uses_original_pixel_dimensions(tmp_path):
    files = _inputs(tmp_path)
    originals = [file.read_bytes() for file in files]
    png, quality = tmp_path / "native.png", tmp_path / "native.json"
    result = compose_native_rgb_segment(files, png, quality)
    assert result.image.shape[:2] == (260, 340)
    with Image.open(png) as output:
        assert output.size == (340, 260)
    assert [file.read_bytes() for file in files] == originals


def test_native_canvas_limit_fails_without_outputs(tmp_path):
    files = _inputs(tmp_path)
    png, quality = tmp_path / "native.png", tmp_path / "native.json"
    with pytest.raises(ValueError, match="canvas limit"):
        compose_native_rgb_segment(files, png, quality, max_canvas_pixels=100)
    assert not png.exists() and not quality.exists()
