"""Surveyed planar native RGB and thermal orthophoto regression tests."""
from pathlib import Path

import cv2
import numpy as np
import pytest
import rasterio

from mcm_solarcheck.services.orthomosaic_geotiff_contract import GeoTIFFSpatialReference
from mcm_solarcheck.services.orthophoto_planar_export import export_planar_orthophoto
from mcm_solarcheck.services.orthophoto_planar_rectification import SurveyedFrame


def _frame(tmp_path, *, thermal=False, surveyed=True):
    path = tmp_path / ("thermal.png" if thermal else "rgb.png")
    values = (
        np.full((8, 8), 71, dtype=np.uint8) if thermal
        else np.full((8, 8, 3), (5, 10, 20), dtype=np.uint8)
    )
    assert cv2.imwrite(str(path), values)
    # Identity control in pixel/world grid: pixel centres 0..7.
    points = ((0., 0.), (7., 0.), (7., 7.), (0., 7.))
    return SurveyedFrame(path, points, points, controls_surveyed=surveyed)


def _reference():
    return GeoTIFFSpatialReference("EPSG:25832", (1., 0., 0., 0., 1., 0.), 8, 8)


def test_native_rgb_and_thermal_exports_are_distinct_geotiffs(tmp_path):
    rgb = export_planar_orthophoto(
        (_frame(tmp_path),), tmp_path / "rgb-ortho.tif", _reference(),
        planar_surface_verified=True,
    )
    thermal = export_planar_orthophoto(
        (_frame(tmp_path, thermal=True),), tmp_path / "thermal-ortho.tif",
        _reference(), thermal=True, planar_surface_verified=True,
    )
    with rasterio.open(rgb) as source:
        assert source.count == 3 and source.crs.to_epsg() == 25832
        assert tuple(source.read()[:, 4, 4]) == (20, 10, 5)
    with rasterio.open(thermal) as source:
        assert source.count == 1 and source.read(1)[4, 4] == 71
        assert source.tags()["MCM_THERMAL_CALIBRATION"] == "unverified"


def test_rejects_unverified_controls_or_surface_and_never_overwrites(tmp_path):
    destination = tmp_path / "ortho.tif"
    with pytest.raises(ValueError, match="surface"):
        export_planar_orthophoto((_frame(tmp_path),), destination, _reference())
    with pytest.raises(ValueError, match="surveyed"):
        export_planar_orthophoto(
            (_frame(tmp_path, surveyed=False),), destination, _reference(),
            planar_surface_verified=True,
        )
    assert not destination.exists()
    export_planar_orthophoto(
        (_frame(tmp_path),), destination, _reference(), planar_surface_verified=True,
    )
    with pytest.raises(FileExistsError):
        export_planar_orthophoto(
            (_frame(tmp_path),), destination, _reference(), planar_surface_verified=True,
        )


def test_reject_collinear_control_points(tmp_path):
    from mcm_solarcheck.services.orthophoto_planar_rectification import rectify_planar_frame
    frame = _frame(tmp_path)
    line = ((0., 0.), (2., 0.), (4., 0.), (7., 0.))
    invalid = SurveyedFrame(frame.image_path, line, line, controls_surveyed=True)
    with pytest.raises(ValueError, match='non-collinear'):
        rectify_planar_frame(invalid, _reference())


def test_reject_invalid_mosaic_pixel_limit(tmp_path):
    from mcm_solarcheck.services.orthophoto_planar_mosaic import build_planar_orthophoto
    frame = _frame(tmp_path)
    with pytest.raises(ValueError, match='max_pixels'):
        build_planar_orthophoto((frame,), _reference(), max_pixels=0)
    with pytest.raises(ValueError, match='pixel limit'):
        build_planar_orthophoto((frame,), _reference(), max_pixels=63)
