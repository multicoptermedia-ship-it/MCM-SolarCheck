"""Synthetic JPEG archive checks without customer photos or GPS data."""
from io import BytesIO
from zipfile import ZipFile

from PIL import Image
import pytest

from mcm_solarcheck.services.flight_image_readiness import inspect_flight_image_readiness


def _jpeg(mode, size):
    out = BytesIO()
    Image.new(mode, size).save(out, format="JPEG")
    return out.getvalue()


def _archive(tmp_path, thermal_mode="RGB"):
    path = tmp_path / "images.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("DJI_20260725154422_0001_V.JPG", _jpeg("RGB", (40, 30)))
        archive.writestr("DJI_20260725154422_0001_T.JPG", _jpeg(thermal_mode, (16, 12)))
    return path


def test_multichannel_thermal_requires_radiometric_verification(tmp_path):
    result = inspect_flight_image_readiness(_archive(tmp_path))
    assert (result.rgb_images, result.thermal_images) == (1, 1)
    assert result.rgb_dimensions == ((40, 30),)
    assert result.thermal_dimensions == ((16, 12),)
    assert result.thermal_palette_images == 1
    assert not result.ready_for_metric_orthophoto


def test_single_band_is_not_automatically_temperature_calibrated(tmp_path):
    result = inspect_flight_image_readiness(_archive(tmp_path, "L"))
    assert result.thermal_palette_images == 0
    assert not result.ready_for_metric_orthophoto


def test_invalid_jpeg_is_rejected(tmp_path):
    path = tmp_path / "bad.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("DJI_20260725154422_0001_T.JPG", b"not a jpeg")
    with pytest.raises(ValueError, match="unreadable"):
        inspect_flight_image_readiness(path)
