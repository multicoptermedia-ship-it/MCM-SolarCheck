"""GIS-aware RGB/thermal layer alignment regression tests."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from mcm_solarcheck.services.orthophoto_layer_alignment import (
    aligned_preview_arrays, inspect_orthophoto_layer_pair,
)


def _raster(path, values, *, transform, crs="EPSG:25832"):
    with rasterio.open(
        path, "w", driver="GTiff", height=values.shape[1], width=values.shape[2],
        count=values.shape[0], dtype=values.dtype, crs=crs, transform=transform,
    ) as dst:
        dst.write(values)
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
