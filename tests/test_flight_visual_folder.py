"""Bounded automatic folder workflow tests, using synthetic private-free images."""
import json

import numpy as np
import pytest
from PIL import Image

from mcm_solarcheck.services.flight_visual_folder import (
    discover_rgb_images, preview_rgb_folder,
)


def _folder(tmp_path, count):
    image = np.random.default_rng(991).integers(0, 256, (260, 340, 3), dtype=np.uint8)
    for index in range(1, count + 1):
        Image.fromarray(image).save(
            tmp_path / f"DJI_20260725154421_{index:04d}_V.JPG", quality=95
        )
        Image.fromarray(image).save(
            tmp_path / f"DJI_20260725154421_{index:04d}_T.JPG", quality=95
        )
    return tmp_path


def test_auto_discovers_and_processes_all_three_rgb_frames(tmp_path):
    folder = _folder(tmp_path, 3)
    paths = discover_rgb_images(folder)
    assert [path.stem[-6:] for path in paths] == [
        "0001_V", "0002_V", "0003_V"
    ]
    png, quality = tmp_path / "preview.png", tmp_path / "quality.json"
    preview_rgb_folder(folder, png, quality)
    assert png.is_file()
    assert json.loads(quality.read_text())["preview_only"] is True


def test_refuses_to_silently_drop_images_in_larger_flight(tmp_path):
    folder = _folder(tmp_path, 5)
    with pytest.raises(ValueError, match="whole-flight processing"):
        preview_rgb_folder(folder, tmp_path / "preview.png", tmp_path / "quality.json")
    assert not (tmp_path / "preview.png").exists()


def test_rejects_duplicate_rgb_ids(tmp_path):
    folder = _folder(tmp_path, 3)
    (folder / "DJI_20260725154422_0001_V.JPG").write_bytes(
        (folder / "DJI_20260725154421_0001_V.JPG").read_bytes()
    )
    with pytest.raises(ValueError, match="duplicate"):
        discover_rgb_images(folder)
