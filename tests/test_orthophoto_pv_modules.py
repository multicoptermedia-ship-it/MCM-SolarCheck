"""Existing PV detector -> bounded native GeoTIFF windows -> GIS proposals."""
from hashlib import sha256
import json
from math import atan, degrees, radians, sinh, tan, asinh

import cv2
import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine, from_origin, xy as raster_center_xy

from mcm_solarcheck.services.orthophoto_pv_modules import detect_orthophoto_pv_window
from mcm_solarcheck.vision.detection import ModuleDetection


def _xy(transform, x, y):
    return (transform.a*x + transform.b*y + transform.c,
            transform.d*x + transform.e*y + transform.f)


def _raster(path, values, transform, *, crs="EPSG:3857", nodata=None, mask=None):
    with rasterio.open(
        path, "w", driver="GTiff", width=values.shape[2], height=values.shape[1],
        count=len(values), dtype=values.dtype, transform=transform, crs=crs, nodata=nodata,
    ) as output:
        output.write(values)
        if mask is not None:
            output.write_mask(mask.astype(np.uint8)*255)
    return path


def _pv_rgb():
    image = np.full((600, 800, 3), 230, np.uint8)
    cv2.rectangle(image, (100, 100), (180, 150), (120, 70, 40), -1)
    cv2.rectangle(image, (400, 300), (480, 350), (120, 70, 40), -1)
    return np.moveaxis(image[:, :, ::-1], -1, 0)


def _fixed_detector(*polygons):
    class FixedDetector:
        name = "controlled_geometry_for_GIS_tests"
        def detect_array(self, image):
            assert image.dtype == np.uint8 and image.shape[2] == 3
            return tuple(ModuleDetection(tuple(polygon), .9) for polygon in polygons)
    return FixedDetector()


def test_existing_detector_native_roi_maps_to_different_crs_without_full_reads(tmp_path, monkeypatch):
    """Real detector and real rasters; known Web-Mercator formula is the oracle."""
    earth_radius = 6378137.
    rgb_transform = from_origin(700000., 6500000., .1, .1)
    left = degrees(700000./earth_radius)
    right = degrees(700080./earth_radius)
    top = degrees(atan(sinh(6500000./earth_radius)))
    bottom = degrees(atan(sinh(6499940./earth_radius)))
    thermal_transform = from_origin(left, top, (right-left)/400, (top-bottom)/300)
    rgb = _raster(tmp_path/"private-rgb.tif", _pv_rgb(), rgb_transform)
    thermal = _raster(tmp_path/"private-thermal.tif", np.ones((1, 300, 400), np.float32),
                      thermal_transform, crs="EPSG:4326")
    original_hashes = tuple(sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal))

    real_open, reads = rasterio.open, []
    class WindowOnlyDataset:
        def __init__(self, dataset): self.dataset = dataset
        def __enter__(self): self.dataset.__enter__(); return self
        def __exit__(self, *args): return self.dataset.__exit__(*args)
        def __getattr__(self, name): return getattr(self.dataset, name)
        def read(self, *args, **kwargs):
            assert kwargs.get("window") is not None
            assert "out_shape" not in kwargs  # Native resolution only.
            reads.append(kwargs["window"])
            return self.dataset.read(*args, **kwargs)
        def dataset_mask(self, *args, **kwargs):
            assert kwargs.get("window") is not None
            return self.dataset.dataset_mask(*args, **kwargs)
    monkeypatch.setattr(rasterio, "open", lambda *a, **kw: WindowOnlyDataset(real_open(*a, **kw)))
    monkeypatch.setattr(cv2, "imread", lambda *a, **kw: pytest.fail("full TIFF/OpenCV file read"))

    result = detect_orthophoto_pv_window(rgb, thermal, window=(80, 60, 640, 480))
    assert len(result.proposals) == 2
    assert reads[0].width == 640 and reads[0].height == 480
    assert all(w.width*w.height <= 1_000_000 for w in reads[1:])
    first = min(result.proposals, key=lambda p: min(x for x, _ in p.rgb_polygon_px))
    center = np.mean(first.rgb_polygon_px, axis=0)
    np.testing.assert_allclose(center, (140., 125.), atol=1.)
    for x, y in first.rgb_polygon_px:
        east, north = raster_center_xy(rgb_transform, y, x, offset="center")
        lon = degrees(east/earth_radius)
        lat = degrees(atan(sinh(north/earth_radius)))
        expected = np.asarray(_xy(~thermal_transform, lon, lat)) - .5
        assert np.linalg.norm(np.asarray(first.thermal_polygon_px)-expected, axis=1).min() < 1.e-7
    for tx, ty in first.thermal_polygon_px:
        lon, lat = raster_center_xy(thermal_transform, ty, tx, offset="center")
        original = np.asarray(_xy(~rgb_transform, earth_radius*radians(lon),
                                 earth_radius*asinh(tan(radians(lat))))) - .5
        assert 100 <= original[0] <= 180 and 100 <= original[1] <= 150
    assert all(p.thermal_valid_coverage == 1. for p in result.proposals)
    assert all(p.review_status == "pending" for p in result.proposals)
    report = result.summary()
    assert report["module_proposal_count"] == 2
    assert report["thermal_values_interpreted"] is False
    assert all(value is False for key, value in report.items() if key.endswith("verified"))
    for forbidden in (str(tmp_path), "private-rgb", "private-thermal", "700000", "polygon"):
        assert forbidden not in json.dumps(report)
    assert tuple(sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal)) == original_hashes


def test_thermal_nan_nodata_and_gdal_mask_each_reduce_native_polygon_coverage(tmp_path):
    rgb = _raster(tmp_path/"rgb.tif", np.full((3, 100, 100), 100, np.uint8),
                  from_origin(350000, 5650000, 1, 1), crs="EPSG:25832")
    values = np.full((1, 100, 100), 99., np.float32)
    values[0, 10:30, 10:30] = np.nan
    values[0, 30:50, 10:30] = -9999.
    valid = np.ones((100, 100), bool)
    valid[10:30, 30:50] = False
    thermal = _raster(tmp_path/"thermal.tif", values, from_origin(350000, 5650000, 1, 1),
                      crs="EPSG:25832", nodata=-9999., mask=valid)
    # Explicit GDAL masks override nodata masks. Both the declared sentinel
    # and actual NaNs nevertheless need to remain invalid thermal pixels.
    # Edges at half-index coordinates surround native pixel centers 10..49.
    polygon = ((9.5, 9.5), (49.5, 9.5), (49.5, 49.5), (9.5, 49.5))
    result = detect_orthophoto_pv_window(rgb, thermal, window=(0, 0, 100, 100),
                                        detector=_fixed_detector(polygon))
    proposal, = result.proposals
    assert proposal.thermal_polygon_sample_count == 1600
    assert proposal.thermal_valid_pixel_count == 400
    assert proposal.thermal_valid_coverage == .25
    assert result.summary()["proposals_with_partial_thermal_coverage"] == 1


def test_rgb_nodata_proposal_rejected_and_outside_thermal_has_zero_coverage(tmp_path):
    rgb_valid = np.ones((100, 100), bool)
    rgb_valid[15, 15] = False
    rgb = _raster(tmp_path/"rgb.tif", np.full((3, 100, 100), 100, np.uint8),
                  from_origin(1000, 2000, 1, 1), mask=rgb_valid)
    thermal = _raster(tmp_path/"thermal.tif", np.ones((1, 20, 20), np.float32),
                      from_origin(1000, 2000, 1, 1))
    detector = _fixed_detector(
        ((10., 10.), (30., 10.), (30., 30.), (10., 30.)),
        ((60., 60.), (80., 60.), (80., 80.), (60., 80.)),
    )
    result = detect_orthophoto_pv_window(rgb, thermal, window=(0, 0, 100, 100), detector=detector)
    assert result.rejected_rgb_nodata_count == 1
    proposal, = result.proposals
    assert proposal.thermal_valid_coverage == 0.
    assert proposal.thermal_valid_pixel_count == 0
    assert proposal.thermal_polygon_sample_count == 400
    assert result.summary()["proposals_without_thermal_coverage"] == 1


def test_declared_bgr_band_order_and_single_band_nodata_are_respected(tmp_path):
    values = np.zeros((3, 100, 100), np.uint8)
    values[:] = np.asarray((120, 70, 40), np.uint8)[:, None, None]
    values[1, 15, 15] = 0  # Only one stored band is NoData.
    rgb = _raster(tmp_path/"bgr.tif", values, from_origin(1000, 2000, 1, 1),
                  nodata=0, mask=np.ones((100, 100), bool))
    with rasterio.open(rgb, "r+") as output:
        output.colorinterp = (rasterio.enums.ColorInterp.blue,
                              rasterio.enums.ColorInterp.green,
                              rasterio.enums.ColorInterp.red)
    thermal = _raster(tmp_path/"thermal.tif", np.ones((1, 100, 100), np.float32),
                      from_origin(1000, 2000, 1, 1))
    class CheckColors:
        def detect_array(self, image):
            np.testing.assert_array_equal(image[20, 20], (120, 70, 40))
            return (
                ModuleDetection(((10., 10.), (30., 10.), (30., 30.), (10., 30.)), .9),
                ModuleDetection(((60., 60.), (80., 60.), (80., 80.), (60., 80.)), .9),
            )
    result = detect_orthophoto_pv_window(rgb, thermal, window=(0, 0, 100, 100),
                                        detector=CheckColors())
    assert result.rejected_rgb_nodata_count == 1
    assert len(result.proposals) == 1
    assert result.proposals[0].thermal_valid_coverage == 1.


def test_rotated_affines_map_real_native_pixel_coordinates(tmp_path):
    rgb_transform = Affine(1., .2, 1000., .1, -1., 2000.)
    thermal_transform = Affine(2., .4, 995., .2, -2., 2005.)
    rgb = _raster(tmp_path/"rgb.tif", np.full((3, 100, 100), 100, np.uint8), rgb_transform)
    thermal = _raster(tmp_path/"thermal.tif", np.ones((1, 100, 100), np.uint16), thermal_transform)
    local = ((10., 10.), (30., 10.), (30., 30.), (10., 30.))
    result = detect_orthophoto_pv_window(rgb, thermal, window=(20, 30, 60, 60),
                                        detector=_fixed_detector(local))
    proposal, = result.proposals
    for x, y in proposal.rgb_polygon_px:
        world = raster_center_xy(rgb_transform, y, x, offset="center")
        expected = np.asarray(_xy(~thermal_transform, *world)) - .5
        assert np.linalg.norm(np.asarray(proposal.thermal_polygon_px)-expected, axis=1).min() < 1.e-9
    assert proposal.thermal_valid_coverage == 1.


def test_unequal_resolution_converts_pixel_centers_not_corners(tmp_path):
    rgb_transform = from_origin(1000., 2000., 1., 1.)
    thermal_transform = from_origin(1000., 2000., 2., 2.)
    rgb = _raster(tmp_path/"rgb.tif", np.full((3, 64, 64), 100, np.uint8), rgb_transform)
    thermal = _raster(tmp_path/"thermal.tif", np.ones((1, 64, 64), np.float32), thermal_transform)
    polygon = ((20., 20.), (40., 20.), (40., 40.), (20., 40.))
    result = detect_orthophoto_pv_window(rgb, thermal, window=(0, 0, 64, 64),
                                        detector=_fixed_detector(polygon))
    proposal, = result.proposals
    world_center = raster_center_xy(rgb_transform, 20, 20, offset="center")
    assert world_center == (1020.5, 1979.5)
    expected = np.asarray(_xy(~thermal_transform, *world_center)) - .5
    np.testing.assert_array_equal(expected, (9.75, 9.75))
    np.testing.assert_array_equal(proposal.thermal_polygon_px[0], expected)
    # In the same CRS, round-trip the returned thermal center to the original
    # world center. Direct corner mapping would return (10, 10) and fail here.
    np.testing.assert_array_equal(
        raster_center_xy(thermal_transform, proposal.thermal_polygon_px[0][1],
                         proposal.thermal_polygon_px[0][0], offset="center"),
        world_center,
    )
    assert proposal.thermal_valid_coverage == 1.


def test_huge_resolution_ratio_is_refused_before_unbounded_thermal_read(tmp_path):
    rgb = _raster(tmp_path/"rgb.tif", np.full((3, 100, 100), 100, np.uint8),
                  from_origin(1000, 2000, 1, 1))
    thermal = _raster(tmp_path/"thermal.tif", np.ones((1, 2, 2), np.uint8),
                      from_origin(1000, 2000, 1.e-5, 1.e-5))
    detector = _fixed_detector(((10., 10.), (30., 10.), (30., 30.), (10., 30.)))
    with pytest.raises(ValueError, match="pixel budget"):
        detect_orthophoto_pv_window(rgb, thermal, window=(0, 0, 100, 100), detector=detector)


def test_invalid_window_and_cancellation_do_not_read_customer_rasters(tmp_path):
    for window in ((0, 0, 2049, 2), (False, 0, 20, 20), (-1, 0, 20, 20)):
        with pytest.raises(ValueError, match="window"):
            detect_orthophoto_pv_window(tmp_path/"absent.tif", tmp_path/"absent2.tif", window=window)
    with pytest.raises(RuntimeError, match="cancelled"):
        detect_orthophoto_pv_window(tmp_path/"absent.tif", tmp_path/"absent2.tif",
                                    window=(0, 0, 10, 10), should_cancel=lambda: True)
