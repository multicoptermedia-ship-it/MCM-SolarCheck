"""Synthetic image overlap checks; never commit actual inspection imagery."""
from zipfile import ZipFile
from io import BytesIO

import numpy as np
import cv2
from PIL import Image
import pytest

from mcm_solarcheck.services.flight_overlap_audit import audit_flight_overlap


def _jpeg(array):
    out = BytesIO()
    Image.fromarray(array).save(out, format="JPEG", quality=95)
    return out.getvalue()


def _zip(tmp_path, images):
    path = tmp_path / "flight.zip"
    with ZipFile(path, "w") as archive:
        for i, array in enumerate(images, 1):
            archive.writestr(f"DJI_202607251544{i:02d}_{i:04d}_V.JPG", _jpeg(array))
    return path


def test_identical_textured_images_have_geometric_correspondences(tmp_path):
    rng = np.random.default_rng(22)
    image = rng.integers(0, 256, size=(240, 320), dtype=np.uint8)
    audit = audit_flight_overlap(_zip(tmp_path, [image, image]))
    assert len(audit.rgb) == 1
    assert audit.rgb[0].matches >= 20
    assert audit.rgb[0].inliers >= 10
    assert audit.metric_roof_coverage_verified is False


def test_featureless_images_fail_closed_without_crashing(tmp_path):
    image = np.zeros((240, 320), dtype=np.uint8)
    audit = audit_flight_overlap(_zip(tmp_path, [image, image]))
    assert audit.rgb[0].matches == 0
    assert audit.rgb[0].inliers == 0
    assert any("weak" in note for note in audit.diagnostics)


def test_frame_limit_is_enforced(tmp_path):
    image = np.zeros((240, 320), dtype=np.uint8)
    with pytest.raises(ValueError, match="frame limit"):
        audit_flight_overlap(_zip(tmp_path, [image, image, image]), max_frames=2)
