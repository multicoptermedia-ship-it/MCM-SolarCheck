"""End-to-end native planar orthophoto export from imported frames."""
import cv2
import numpy as np
import rasterio

from mcm_solarcheck.domain.models import ImageFrame, ThermalFrame
from mcm_solarcheck.services.orthomosaic_geotiff_contract import GeoTIFFSpatialReference
from mcm_solarcheck.services.orthophoto_imported_frames import ImportedSurveyedControl
from mcm_solarcheck.services.orthophoto_imported_pair import generate_imported_planar_orthophoto_pair


def test_imported_rgb_and_thermal_generate_distinct_geotiffs(tmp_path):
    rgb_path = tmp_path / "rgb.png"
    thermal_path = tmp_path / "thermal.png"
    assert cv2.imwrite(str(rgb_path), np.full((8, 8, 3), (5, 10, 20), dtype=np.uint8))
    assert cv2.imwrite(str(thermal_path), np.full((8, 8), 2048, dtype=np.uint16))
    points = ((0., 0.), (7., 0.), (7., 7.), (0., 7.))
    rgb_control = ImportedSurveyedControl("rgb", points, points, True)
    thermal_control = ImportedSurveyedControl("thermal", points, points, True)
    reference = GeoTIFFSpatialReference("EPSG:25832", (1., 0., 0., 0., 1., 0.), 8, 8)
    result = generate_imported_planar_orthophoto_pair(
        (ImageFrame("rgb", rgb_path, width=8, height=8),),
        (ThermalFrame("thermal", thermal_path, width=8, height=8),),
        (rgb_control,), (thermal_control,), reference, reference,
        tmp_path / "rgb-ortho.tif", tmp_path / "thermal-ortho.tif",
        planar_surface_verified=True,
    )
    with rasterio.open(result.rgb_geotiff) as rgb:
        assert rgb.count == 3
        assert rgb.crs.to_epsg() == 25832
        assert tuple(rgb.read()[:, 4, 4]) == (20, 10, 5)
    with rasterio.open(result.thermal_geotiff) as thermal:
        assert thermal.count == 1
        assert thermal.dtypes == ("uint16",)
        assert int(thermal.read(1)[4, 4]) == 2048
        assert thermal.tags()["MCM_THERMAL_CALIBRATION"] == "unverified"


def test_reject_same_output_path_before_any_export(tmp_path):
    import pytest
    reference = GeoTIFFSpatialReference("EPSG:25832", (1., 0., 0., 0., 1., 0.), 8, 8)
    destination = tmp_path / "same.tif"
    with pytest.raises(ValueError, match="distinct"):
        generate_imported_planar_orthophoto_pair(
            (), (), (), (), reference, reference, destination, destination,
            planar_surface_verified=True,
        )
    assert not destination.exists()


def test_invalid_second_target_does_not_create_first_output(tmp_path):
    import pytest
    reference = GeoTIFFSpatialReference("EPSG:25832", (1., 0., 0., 0., 1., 0.), 8, 8)
    first = tmp_path / "rgb.tif"
    with pytest.raises(ValueError, match="GeoTIFF"):
        generate_imported_planar_orthophoto_pair(
            (), (), (), (), reference, reference, first, tmp_path / "thermal.png",
            planar_surface_verified=True,
        )
    assert not first.exists()
