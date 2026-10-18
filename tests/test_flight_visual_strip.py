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


def test_projective_zip_writes_nonmetric_png_and_rejects_overwrite(tmp_path):
    image = np.random.default_rng(741).integers(0, 256, (260, 340, 3), dtype=np.uint8)
    buf = BytesIO()
    Image.fromarray(image).save(buf, format="JPEG", quality=95)
    archive_path = tmp_path / "projective.zip"
    with ZipFile(archive_path, "w") as archive:
        for i in (1, 2, 3):
            archive.writestr(f"DJI_20260725154421_000{i}_V.JPG", buf.getvalue())
    output = tmp_path / "projective.png"
    counts = preview_rgb_strip(archive_path, ["0001", "0002", "0003"], output, projective=True)
    assert counts == ()
    assert output.is_file()
    assert cv2.imread(str(output)) is not None
    with pytest.raises(ValueError, match="new PNG"):
        preview_rgb_strip(archive_path, ["0001", "0002", "0003"], output, projective=True)


def test_projective_cli_rejects_conflicting_options_without_output(tmp_path):
    output = tmp_path / "not_written.png"
    with pytest.raises(FileNotFoundError):
        preview_rgb_strip(tmp_path / "missing.zip", ["0001", "0002"], output, projective=True)
    assert not output.exists()


def test_projective_zip_writes_explicit_nonmetric_quality_json(tmp_path):
    import json
    image = np.random.default_rng(833).integers(0, 256, (260, 340, 3), dtype=np.uint8)
    buf = BytesIO()
    Image.fromarray(image).save(buf, format="JPEG", quality=95)
    archive_path = tmp_path / "flight.zip"
    with ZipFile(archive_path, "w") as archive:
        for i in (1, 2, 3):
            archive.writestr(f"DJI_20260725154421_000{i}_V.JPG", buf.getvalue())
    png = tmp_path / "preview.png"
    quality = tmp_path / "quality.json"
    assert preview_rgb_strip(archive_path, ["0001", "0002", "0003"], png,
                             projective=True, quality_json_path=quality) == ()
    data = json.loads(quality.read_text(encoding="utf-8"))
    assert png.is_file()
    assert data["preview_only"] is True
    assert data["metric_orthophoto_verified"] is False
    assert data["temperature_calibrated"] is False
    assert data["multiply_covered_pixels"] > 0
    assert data["mean_overlap_disagreement_0_255"] is not None
    assert "DJI_" not in quality.read_text(encoding="utf-8")


def test_quality_json_requires_projective_and_does_not_overwrite(tmp_path):
    archive = tmp_path / "missing.zip"
    png = tmp_path / "preview.png"
    quality = tmp_path / "quality.json"
    with pytest.raises(ValueError, match="requires --projective"):
        preview_rgb_strip(archive, ["0001", "0002"], png, quality_json_path=quality)
    quality.write_text("existing", encoding="utf-8")
    with pytest.raises(ValueError, match="new JSON"):
        preview_rgb_strip(archive, ["0001", "0002", "0003"], png,
                          projective=True, quality_json_path=quality)
    assert quality.read_text(encoding="utf-8") == "existing"
    assert not png.exists()
