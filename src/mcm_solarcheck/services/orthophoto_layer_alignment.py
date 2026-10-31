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
    thermal_kind: str = "sensor_values"
    rgb_bands: tuple[int, int, int] = (1, 2, 3)
    thermal_bands: tuple[int, ...] = (1,)


def _rgb_band_indices(dataset, *, thermal=False):
    """Use declared RGB order; unlabelled uint8 RGB exports remain usable.

    Three arbitrary sensor bands must not silently become temperatures or a
    display raster. A 16-bit/float multi-band thermal dataset is ambiguous and
    needs a separate explicit data contract before analysis.
    """
    from rasterio.enums import ColorInterp
    colors = tuple(dataset.colorinterp)
    declared = (ColorInterp.red, ColorInterp.green, ColorInterp.blue)
    if all(color in colors for color in declared):
        bands = tuple(colors.index(color)+1 for color in declared)
    else:
        allowed = {ColorInterp.undefined, ColorInterp.gray, ColorInterp.alpha}
        if dataset.count not in (3, 4) or not set(colors) <= allowed:
            raise ValueError("RGB display needs three identifiable RGB bands")
        bands = (1, 2, 3)
    if any(dataset.dtypes[index-1] != "uint8" for index in bands):
        kind = "Thermal RGB display" if thermal else "RGB preview"
        raise ValueError(f"{kind} requires uint8 RGB bands")
    return bands


def _thermal_bands(dataset):
    from rasterio.enums import ColorInterp
    non_alpha = tuple(i+1 for i, color in enumerate(dataset.colorinterp)
                      if color != ColorInterp.alpha)
    if len(non_alpha) == 1:
        if dataset.dtypes[non_alpha[0]-1].startswith("complex"):
            raise ValueError("Thermal sensor values must be real numeric samples")
        return "sensor_values", non_alpha
    if dataset.count in (3, 4):
        return "visual_rgb", _rgb_band_indices(dataset, thermal=True)
    raise ValueError("Thermal raster needs one sensor band or uint8 RGB display bands")


def inspect_orthophoto_layer_pair(rgb_path: str | Path, thermal_path: str | Path) -> OrthophotoLayerPair:
    """Require two distinct valid GIS rasters; retain native CRS and transforms."""
    import rasterio
    rgb = Path(rgb_path).resolve(strict=True)
    thermal = Path(thermal_path).resolve(strict=True)
    if rgb.samefile(thermal):
        raise ValueError("RGB and thermal orthophotos must be distinct files")
    rgb_reference = inspect_existing_geotiff(rgb)
    thermal_reference = inspect_existing_geotiff(thermal)
    with rasterio.open(rgb) as rgb_dataset, rasterio.open(thermal) as thermal_dataset:
        rgb_bands = _rgb_band_indices(rgb_dataset)
        thermal_kind, thermal_bands = _thermal_bands(thermal_dataset)
    return OrthophotoLayerPair(
        rgb, thermal, rgb_reference, thermal_reference,
        thermal_kind, rgb_bands, thermal_bands,
    )


def aligned_preview_arrays(
    pair: OrthophotoLayerPair, *, max_dimension: int = 1024
):
    """Return bounded RGB and uncalibrated thermal arrays on the RGB grid.

    Scalar thermal samples remain float HxW. Visual RGB thermal samples use
    float HxWx3 and retain their source colors. Invalid thermal OR RGB pixels
    are NaN in the returned thermal layer. No samples imply Celsius calibration.
    Standard GDAL reprojection handles spatial geometry and dataset masks;
    declared alpha bands are separately reprojected as validity masks.
    """
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject
    from rasterio.transform import Affine
    from rasterio.enums import ColorInterp

    if not isinstance(max_dimension, int) or isinstance(max_dimension, bool) or max_dimension < 1 or max_dimension > 4096:
        raise ValueError("Preview dimension must be between 1 and 4096")
    with rasterio.open(pair.rgb_path) as rgb, rasterio.open(pair.thermal_path) as thermal:
        rgb_bands = _rgb_band_indices(rgb)
        thermal_kind, thermal_bands = _thermal_bands(thermal)
        if (pair.thermal_kind != thermal_kind or pair.rgb_bands != rgb_bands
                or pair.thermal_bands != thermal_bands):
            raise ValueError("Orthophoto band layout changed since inspection")
        scale = min(1.0, max_dimension / max(rgb.width, rgb.height))
        width = max(1, round(rgb.width * scale))
        height = max(1, round(rgb.height * scale))
        rgb_pixels = rgb.read(rgb_bands, out_shape=(3, height, width),
                              resampling=Resampling.bilinear)
        rgb_image = np.moveaxis(rgb_pixels, 0, -1)
        rgb_valid = np.all(rgb.read_masks(
            rgb_bands, out_shape=(3, height, width),
            resampling=Resampling.nearest) > 0, axis=0)
        for index, color in enumerate(rgb.colorinterp, 1):
            if color == ColorInterp.alpha:
                rgb_valid &= rgb.read(index, out_shape=(height, width),
                                      resampling=Resampling.nearest) > 0
        rgb_image[~rgb_valid] = 0
        transform = rgb.transform * Affine.scale(rgb.width / width, rgb.height / height)
        def warp_band(index, *, nodata, destination_nodata):
            values = np.full((height, width), destination_nodata, dtype=np.float32)
            reproject(
                source=rasterio.band(thermal, index), destination=values,
                src_transform=thermal.transform, src_crs=thermal.crs,
                src_nodata=nodata, dst_transform=transform, dst_crs=rgb.crs,
                dst_nodata=destination_nodata, resampling=Resampling.nearest,
            )
            return values

        bands = [warp_band(index, nodata=thermal.nodata, destination_nodata=np.nan)
                 for index in thermal_bands]
        common_valid = rgb_valid & np.all(np.isfinite(bands), axis=0)
        for index, color in enumerate(thermal.colorinterp, 1):
            if color == ColorInterp.alpha:
                common_valid &= warp_band(index, nodata=0, destination_nodata=0) > 0
        thermal_values = bands[0] if thermal_kind == "sensor_values" else np.stack(bands, axis=-1)
        thermal_values[~common_valid] = np.nan
    return rgb_image, thermal_values
