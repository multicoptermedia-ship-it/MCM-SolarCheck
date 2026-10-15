"""Geospatial contract for comparing separately generated RGB and thermal orthophotos.

This module aligns existing georeferenced rasters; it does not reconstruct an
orthophoto from drone photographs or claim radiometric calibration.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.services.orthomosaic_geotiff_contract import (
    GeoTIFFSpatialReference, inspect_existing_geotiff,
)


@dataclass(frozen=True)
class OrthophotoLayerPair:
    rgb_path: Path
    thermal_path: Path
    rgb_reference: GeoTIFFSpatialReference
    thermal_reference: GeoTIFFSpatialReference


def inspect_orthophoto_layer_pair(rgb_path: str | Path, thermal_path: str | Path) -> OrthophotoLayerPair:
    """Require two distinct valid GIS rasters; retain native CRS and transforms."""
    rgb = Path(rgb_path).resolve(strict=True)
    thermal = Path(thermal_path).resolve(strict=True)
    if rgb == thermal:
        raise ValueError("RGB and thermal orthophotos must be distinct files")
    return OrthophotoLayerPair(
        rgb, thermal, inspect_existing_geotiff(rgb), inspect_existing_geotiff(thermal)
    )


def aligned_preview_arrays(
    pair: OrthophotoLayerPair, *, max_dimension: int = 1024
):
    """Return RGB uint8 HxWx3 and thermal masked float HxW on the RGB grid.

    The preview is bounded for desktop memory. Reprojection uses actual GIS
    transforms, not pixel-index coincidence. It is not an export or approval.
    """
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject
    from rasterio.windows import transform as window_transform
    from rasterio.transform import Affine

    if not isinstance(max_dimension, int) or isinstance(max_dimension, bool) or max_dimension < 1 or max_dimension > 4096:
        raise ValueError("Preview dimension must be between 1 and 4096")
    with rasterio.open(pair.rgb_path) as rgb, rasterio.open(pair.thermal_path) as thermal:
        if rgb.count < 3 or thermal.count < 1:
            raise ValueError("RGB needs three bands and thermal needs at least one band")
        scale = min(1.0, max_dimension / max(rgb.width, rgb.height))
        width = max(1, round(rgb.width * scale))
        height = max(1, round(rgb.height * scale))
        rgb_pixels = rgb.read((1, 2, 3), out_shape=(3, height, width), resampling=Resampling.bilinear)
        if rgb_pixels.dtype != np.uint8:
            raise ValueError("RGB preview requires uint8 RGB bands")
        rgb_image = np.moveaxis(rgb_pixels, 0, -1)
        transform = rgb.transform * Affine.scale(rgb.width / width, rgb.height / height)
        thermal_values = np.full((height, width), np.nan, dtype=np.float32)
        reproject(
            source=rasterio.band(thermal, 1),
            destination=thermal_values,
            src_transform=thermal.transform, src_crs=thermal.crs,
            src_nodata=thermal.nodata,
            dst_transform=transform, dst_crs=rgb.crs,
            dst_nodata=np.nan,
            resampling=Resampling.nearest,
        )
    return rgb_image, thermal_values
