"""Offline synthetic DJI ZIP integration for experimental visual strips."""
from io import BytesIO
from zipfile import ZipFile

import cv2
import numpy as np
import pytest
from PIL import Image

from mcm_solarcheck.services.flight_visual_strip import preview_rgb_strip


def test_three_frame_zip_writes_nonmetric_png(tmp_path):
    image = np.random.default_rng(37).integers(0, 256, (260, 340, 3), dtype=np.uint8)
    buf = BytesIO()
    Image.fromarray(image).save(buf, format="JPEG", quality=95)
    archive_path = tmp_path / "synthetic.zip"
    with ZipFile(archive_path, "w") as archive:
        for i in (1, 2, 3):
            archive.writestr(f"DJI_2026072515442{i}_000{i}_V.JPG", buf.getvalue())
            archive.writestr(f"DJI_2026072515442{i}_000{i}_T.JPG", buf.getvalue())
    output = tmp_path / "visual_strip.png"
    inliers = preview_rgb_strip(archive_path, ["0001", "0002", "0003"], output)
    assert len(inliers) == 2
    assert min(inliers) >= 12
    assert output.exists()
    assert cv2.imread(str(output)) is not None
    with pytest.raises(ValueError, match="new PNG"):
        preview_rgb_strip(archive_path, ["0001", "0002", "0003"], output)
    with pytest.raises(ValueError, match="distinct"):
        preview_rgb_strip(archive_path, ["0001", "0001"], tmp_path / "another.png")


def test_anchored_loop_audit_writes_only_when_consistent(tmp_path):
    image = np.random.default_rng(37).integers(0, 256, (260, 340, 3), dtype=np.uint8)
    buf = BytesIO()
    Image.fromarray(image).save(buf, format='JPEG', quality=95)
    archive_path = tmp_path / 'synthetic_loops.zip'
    with ZipFile(archive_path, 'w') as archive:
        for i in (1, 2, 3):
            archive.writestr('DJI_20260725154421_000%d_V.JPG' % i, buf.getvalue())
    output = tmp_path / 'audited.png'
    result = preview_rgb_strip(archive_path, ['0001', '0002', '0003'], output, anchored=True, audit_loops=True)
    assert len(result) == 2
    assert output.is_file()
