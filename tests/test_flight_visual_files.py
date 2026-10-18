"""Individual-file ingestion uses the same projective core as ZIP tests."""
import json

import numpy as np
import pytest
from PIL import Image

from mcm_solarcheck.services.flight_visual_files import preview_rgb_files


def _images(tmp_path):
    image = np.random.default_rng(832).integers(0, 256, (260, 340, 3), dtype=np.uint8)
    paths = []
    for i in range(3):
        path = tmp_path / f"frame_{i}.jpg"
        Image.fromarray(image).save(path, quality=95)
        paths.append(path)
    return paths


def test_three_individual_rgb_images_produce_png_and_quality(tmp_path):
    paths = _images(tmp_path)
    png, quality = tmp_path / "preview.png", tmp_path / "quality.json"
    result = preview_rgb_files(paths, png, quality)
    assert png.is_file() and quality.is_file()
    assert result.overlap_quality.multiply_covered_pixels > 0
    record = json.loads(quality.read_text(encoding="utf-8"))
    assert record["preview_only"] is True
    assert record["metric_orthophoto_verified"] is False
    assert record["temperature_calibrated"] is False


def test_individual_inputs_reject_duplicates_without_writing(tmp_path):
    paths = _images(tmp_path)
    png, quality = tmp_path / "preview.png", tmp_path / "quality.json"
    with pytest.raises(ValueError, match="distinct"):
        preview_rgb_files([paths[0], paths[0], paths[1]], png, quality)
    assert not png.exists() and not quality.exists()


def test_individual_inputs_never_overwrite_quality(tmp_path):
    paths = _images(tmp_path)
    png, quality = tmp_path / "preview.png", tmp_path / "quality.json"
    quality.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="new PNG and JSON"):
        preview_rgb_files(paths, png, quality)
    assert quality.read_text(encoding="utf-8") == "keep"
    assert not png.exists()


def test_missing_individual_input_does_not_create_outputs(tmp_path):
    paths = _images(tmp_path)
    paths[1].unlink()
    png, quality = tmp_path / "preview.png", tmp_path / "quality.json"
    with pytest.raises(ValueError, match="local JPEG or PNG"):
        preview_rgb_files(paths, png, quality)
    assert not png.exists() and not quality.exists()
