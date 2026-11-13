"""GIS-aware RGB/thermal layer alignment regression tests."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from mcm_solarcheck.services.orthophoto_layer_alignment import (
    aligned_preview_arrays, inspect_orthophoto_layer_pair,
)


def _raster(path, values, *, transform, crs="EPSG:25832", nodata=None,
            mask=None, colors=None):
    from rasterio.enums import ColorInterp
    options = {"ALPHA": "YES"} if colors and ColorInterp.alpha in colors else {}
    with rasterio.open(
        path, "w", driver="GTiff", height=values.shape[1], width=values.shape[2],
        count=values.shape[0], dtype=values.dtype, crs=crs, transform=transform,
        nodata=nodata,
        **options,
    ) as dst:
        dst.write(values)
        if mask is not None:
            dst.write_mask(mask)
        if colors is not None:
            dst.colorinterp = colors
    return path


def test_layers_reproject_thermal_to_rgb_world_grid(tmp_path):
    rgb = _raster(tmp_path / "rgb.tif", np.zeros((3, 4, 4), dtype=np.uint8),
                  transform=from_origin(350000, 5650000, 1, 1))
    # Shift thermal two metres east: first two RGB columns must remain missing.
    thermal = _raster(tmp_path / "thermal.tif",
                      np.full((1, 4, 2), 42, dtype=np.float32),
                      transform=from_origin(350002, 5650000, 1, 1))
    pair = inspect_orthophoto_layer_pair(rgb, thermal)
    rgb_pixels, heat = aligned_preview_arrays(pair)
    assert rgb_pixels.shape == (4, 4, 3)
    assert np.isnan(heat[:, :2]).all()
    assert (heat[:, 2:] == 42).all()


def test_layer_pair_rejects_same_file(tmp_path):
    rgb = _raster(tmp_path / "rgb.tif", np.zeros((3, 2, 2), dtype=np.uint8),
                  transform=from_origin(350000, 5650000, 1, 1))
    with pytest.raises(ValueError, match="distinct"):
        inspect_orthophoto_layer_pair(rgb, rgb)


def test_preview_is_bounded_and_rejects_invalid_size(tmp_path):
    rgb = _raster(tmp_path / "rgb.tif", np.zeros((3, 8, 8), dtype=np.uint8),
                  transform=from_origin(350000, 5650000, 1, 1))
    thermal = _raster(tmp_path / "thermal.tif", np.ones((1, 8, 8), dtype=np.float32),
                      transform=from_origin(350000, 5650000, 1, 1))
    pair = inspect_orthophoto_layer_pair(rgb, thermal)
    pixels, heat = aligned_preview_arrays(pair, max_dimension=4)
    assert pixels.shape == (4, 4, 3)
    assert heat.shape == (4, 4)
    with pytest.raises(ValueError, match="dimension"):
        aligned_preview_arrays(pair, max_dimension=0)


@pytest.mark.parametrize("mask_kind", ("nodata", "internal", "alpha"))
def test_invalid_rgb_pixels_never_count_as_thermal_overlap(tmp_path, mask_kind):
    from rasterio.enums import ColorInterp
    from mcm_solarcheck.services.orthophoto_pair_audit import audit_orthophoto_pair
    transform = from_origin(100, 100, 1, 1)
    rgb = np.full((4 if mask_kind == "alpha" else 3, 4, 4), 60, np.uint8)
    kwargs = {}
    if mask_kind == "nodata":
        rgb[:, :, :2] = 0
        kwargs["nodata"] = 0
    elif mask_kind == "internal":
        mask = np.full((4, 4), 255, np.uint8)
        mask[:, :2] = 0
        kwargs["mask"] = mask
    else:
        rgb[3] = 255
        rgb[3, :, :2] = 0
        kwargs["colors"] = (ColorInterp.red, ColorInterp.green,
                            ColorInterp.blue, ColorInterp.alpha)
    rgb_path = _raster(tmp_path / "rgb.tif", rgb, transform=transform, **kwargs)
    thermal_path = _raster(tmp_path / "heat.tif", np.full((1, 4, 4), 42, np.float32),
                           transform=transform)
    _, heat = aligned_preview_arrays(inspect_orthophoto_layer_pair(rgb_path, thermal_path))
    assert np.isnan(heat[:, :2]).all()
    assert np.all(heat[:, 2:] == 42)
    audit = audit_orthophoto_pair(rgb_path, thermal_path)
    assert audit.comparison_ready and audit.common_pixel_fraction == .5
    assert not audit.georeferencing_verified and not audit.thermal_calibration_verified


def test_all_nodata_rgb_has_no_comparison_ready_pixels(tmp_path):
    from mcm_solarcheck.services.orthophoto_pair_audit import audit_orthophoto_pair
    transform = from_origin(100, 100, 1, 1)
    rgb = _raster(tmp_path / "empty-rgb.tif", np.zeros((3, 4, 4), np.uint8),
                  transform=transform, nodata=0)
    thermal = _raster(tmp_path / "thermal.tif", np.full((1, 4, 4), 42, np.float32),
                      transform=transform)
    audit = audit_orthophoto_pair(rgb, thermal)
    assert audit.common_pixel_fraction == 0
    assert audit.comparison_ready is False


@pytest.mark.parametrize("mask_kind", ("internal", "nan", "alpha"))
def test_thermal_mask_is_reprojected_with_its_real_spatial_offset(tmp_path, mask_kind):
    from rasterio.enums import ColorInterp
    rgb = _raster(tmp_path / "rgb.tif", np.full((3, 4, 4), 70, np.uint8),
                  transform=from_origin(100, 100, 1, 1))
    heat = np.full((2 if mask_kind == "alpha" else 1, 4, 2), 42, np.float32)
    kwargs = {}
    if mask_kind == "internal":
        mask = np.full((4, 2), 255, np.uint8)
        mask[1, 0] = 0
        kwargs["mask"] = mask
    elif mask_kind == "nan":
        heat[0, 1, 0] = np.nan
        kwargs["nodata"] = np.nan
    else:
        heat[1] = 255
        heat[1, 1, 0] = 0
        kwargs["colors"] = (ColorInterp.gray, ColorInterp.alpha)
    thermal = _raster(tmp_path / "thermal.tif", heat,
                      transform=from_origin(102, 100, 1, 1), **kwargs)
    pair = inspect_orthophoto_layer_pair(rgb, thermal)
    assert pair.thermal_kind == "sensor_values"
    _, aligned = aligned_preview_arrays(pair)
    assert aligned.shape == (4, 4)
    assert np.isnan(aligned[:, :2]).all()
    assert np.isnan(aligned[1, 2])
    assert aligned[1, 3] == 42
    assert np.count_nonzero(np.isfinite(aligned)) == 7


def test_visual_thermal_preserves_all_rgb_colors_alpha_and_pixel_coverage(tmp_path):
    import hashlib
    from rasterio.enums import ColorInterp
    from mcm_solarcheck.services.orthophoto_pair_audit import audit_orthophoto_pair
    rgb = _raster(tmp_path / "rgb.tif", np.full((3, 4, 4), 70, np.uint8),
                  transform=from_origin(100, 100, 1, 1))
    values = np.stack([np.full((4, 2), v, np.uint8) for v in (12, 100, 200, 255)])
    values[3, 0, 0] = 0
    thermal = _raster(tmp_path / "thermal-rgba.tif", values,
                      transform=from_origin(102, 100, 1, 1),
                      colors=(ColorInterp.red, ColorInterp.green,
                              ColorInterp.blue, ColorInterp.alpha))
    before = tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in (rgb, thermal))
    pair = inspect_orthophoto_layer_pair(rgb, thermal)
    assert pair.thermal_kind == "visual_rgb"
    assert pair.thermal_bands == (1, 2, 3)
    _, colors = aligned_preview_arrays(pair)
    assert colors.shape == (4, 4, 3) and colors.dtype == np.float32
    assert np.isnan(colors[:, :2]).all()
    assert np.isnan(colors[0, 2]).all()
    np.testing.assert_array_equal(colors[1, 2], (12, 100, 200))
    audit = audit_orthophoto_pair(rgb, thermal)
    assert audit.thermal_kind == "visual_rgb" and audit.comparison_ready
    assert audit.common_pixel_fraction == 7/16
    assert audit.thermal_calibration_verified is False
    assert tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in (rgb, thermal)) == before


def test_each_rgb_display_band_respects_nodata(tmp_path):
    transform = from_origin(100, 100, 1, 1)
    rgb = _raster(tmp_path / "rgb.tif", np.full((3, 2, 2), 50, np.uint8),
                  transform=transform)
    values = np.full((3, 2, 2), 80, np.uint8)
    values[1, 0, 0] = 0
    heat = _raster(tmp_path / "visual.tif", values, transform=transform, nodata=0)
    _, aligned = aligned_preview_arrays(inspect_orthophoto_layer_pair(rgb, heat))
    assert np.isnan(aligned[0, 0]).all()
    assert np.all(aligned[1, 1] == 80)


def test_declared_rgb_band_order_is_used_in_both_sources(tmp_path):
    from rasterio.enums import ColorInterp
    values = np.stack([np.full((2, 2), v, np.uint8) for v in (10, 20, 30)])
    colors = (ColorInterp.blue, ColorInterp.green, ColorInterp.red)
    rgb = _raster(tmp_path / "rgb.tif", values, transform=from_origin(100, 100, 1, 1), colors=colors)
    heat = _raster(tmp_path / "visual.tif", values, transform=from_origin(100, 100, 1, 1), colors=colors)
    pair = inspect_orthophoto_layer_pair(rgb, heat)
    assert pair.rgb_bands == pair.thermal_bands == (3, 2, 1)
    rgb_pixels, thermal_pixels = aligned_preview_arrays(pair)
    np.testing.assert_array_equal(rgb_pixels[0, 0], (30, 20, 10))
    np.testing.assert_array_equal(thermal_pixels[0, 0], (30, 20, 10))


@pytest.mark.parametrize("bands,dtype", ((2, np.float32), (3, np.uint16), (3, np.float32)))
def test_ambiguous_multiband_sensor_data_is_not_a_thermal_rgb_display(tmp_path, bands, dtype):
    transform = from_origin(100, 100, 1, 1)
    rgb = _raster(tmp_path / "rgb.tif", np.full((3, 2, 2), 50, np.uint8), transform=transform)
    thermal = _raster(tmp_path / "sensor.tif", np.ones((bands, 2, 2), dtype), transform=transform)
    with pytest.raises(ValueError, match="Thermal|RGB"):
        inspect_orthophoto_layer_pair(rgb, thermal)
