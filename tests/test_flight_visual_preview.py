"""Synthetic end-to-end ZIP-to-PNG visual preview tests."""
from io import BytesIO
from zipfile import ZipFile

import cv2
import numpy as np
import pytest
from PIL import Image

from mcm_solarcheck.services.flight_visual_preview import preview_rgb_pair


def _jpeg(array):
    stream = BytesIO()
    Image.fromarray(array).save(stream, format="JPEG", quality=95)
    return stream.getvalue()


def test_offline_pair_preview_writes_png_and_never_overwrites(tmp_path):
    image = np.random.default_rng(17).integers(0, 256, (260, 340, 3), dtype=np.uint8)
    archive_path = tmp_path / "flight.zip"
    with ZipFile(archive_path, "w") as archive:
        for i in (1, 2):
            archive.writestr(f"DJI_2026072515442{i}_000{i}_V.JPG", _jpeg(image))
            archive.writestr(f"DJI_2026072515442{i}_000{i}_T.JPG", _jpeg(image))
    destination = tmp_path / "visual_preview.png"
    inliers = preview_rgb_pair(archive_path, "0001", "0002", destination)
    assert inliers >= 12
    assert destination.is_file()
    decoded = cv2.imread(str(destination))
    assert decoded is not None and decoded.shape[2] == 3
    with pytest.raises(ValueError, match="overwrite"):
        preview_rgb_pair(archive_path, "0001", "0002", destination)
    with pytest.raises(ValueError, match="distinct"):
        preview_rgb_pair(archive_path, "0001", "0001", tmp_path / "other.png")
