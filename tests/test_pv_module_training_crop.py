from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from mcm_solarcheck.services.pv_module_training_crop import (
    ModuleCropReview, export_reviewed_rgb_module_crop,
)
from mcm_solarcheck.services.pv_module_crop_privacy_audit import audit_module_training_crop


def _review():
    return ModuleCropReview("consent-logged", "expert-checked", True, True, (0.1, 0.1, 0.9, 0.9))


def test_crop_drops_source_metadata_and_original_is_unchanged(tmp_path):
    source = tmp_path / "customer-project.png"
    info = PngImagePlugin.PngInfo()
    info.add_text("GPSLatitude", "51.0")
    info.add_text("ProjectName", "customer-secret")
    Image.new("RGB", (128, 128), "red").save(source, pnginfo=info)
    before = source.read_bytes()
    output = export_reviewed_rgb_module_crop(source, tmp_path, _review())
    assert output.output_path.name != source.name
    assert output.status == "privacy_reviewed_not_proven_anonymous"
    assert audit_module_training_crop(output.output_path)
    assert b"customer-secret" not in output.output_path.read_bytes()
    assert source.read_bytes() == before


def test_unreviewed_and_nonmodule_data_rejected():
    with pytest.raises(PermissionError):
        ModuleCropReview("", "expert", True, True, (0, 0, 1, 1))
    with pytest.raises(PermissionError):
        ModuleCropReview("consent", "expert", False, True, (0, 0, 1, 1))


def test_small_crop_rejected_without_writing(tmp_path):
    source = tmp_path / "image.png"
    Image.new("RGB", (64, 64), "white").save(source)
    with pytest.raises(ValueError):
        export_reviewed_rgb_module_crop(source, tmp_path, ModuleCropReview(
            "consent", "expert", True, True, (0, 0, 0.1, 0.1)))
    assert len(list(tmp_path.glob("*.png"))) == 1


def test_audit_rejects_png_with_metadata(tmp_path):
    source = tmp_path / "with-metadata.png"
    info = PngImagePlugin.PngInfo()
    info.add_text("GPS", "secret")
    Image.new("RGB", (64, 64)).save(source, pnginfo=info)
    with pytest.raises(ValueError):
        audit_module_training_crop(source)
