"""Strict metadata gate for genuine GIS-ready orthophoto exports.

This does not generate a GeoTIFF and must not be used to promote RGB previews.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path


@dataclass(frozen=True)
class GeoTIFFSpatialReference:
    crs: str
    transform: tuple[float, float, float, float, float, float]
    width: int
    height: int
    nodata: float | None = None


def validate_geotiff_reference(reference: GeoTIFFSpatialReference) -> None:
    """Fail closed if geospatial metadata cannot describe a usable raster."""
    if not isinstance(reference.crs, str) or not reference.crs.strip():
        raise ValueError("GeoTIFF CRS is required")
    if not isinstance(reference.width, int) or isinstance(reference.width, bool) or reference.width < 1:
        raise ValueError("GeoTIFF width must be positive")
    if not isinstance(reference.height, int) or isinstance(reference.height, bool) or reference.height < 1:
        raise ValueError("GeoTIFF height must be positive")
    if len(reference.transform) != 6 or not all(isfinite(v) for v in reference.transform):
        raise ValueError("GeoTIFF affine transform must be finite")
    a, b, _, d, e, _ = reference.transform
    if abs(a * e - b * d) <= 1e-15:
        raise ValueError("GeoTIFF affine transform must be invertible")
    if reference.nodata is not None and not isfinite(reference.nodata):
        raise ValueError("GeoTIFF NoData must be finite")


def require_geotiff_export_target(path: str | Path, reference: GeoTIFFSpatialReference) -> Path:
    """Validate an explicit GIS export target without writing any file."""
    target = Path(path)
    if target.suffix.lower() not in (".tif", ".tiff"):
        raise ValueError("GIS orthophoto export requires a GeoTIFF target")
    validate_geotiff_reference(reference)
    if not target.parent.is_dir():
        raise ValueError("GeoTIFF output directory does not exist")
    if target.exists():
        raise FileExistsError("GeoTIFF export target already exists")
    return target


def geotiff_world_corners(
    reference: GeoTIFFSpatialReference,
) -> tuple[tuple[float, float], ...]:
    """Return outer raster corners in the declared CRS, including rotation/shear."""
    validate_geotiff_reference(reference)
    a, b, c, d, e, f = reference.transform
    pixels = ((0, 0), (reference.width, 0),
              (reference.width, reference.height), (0, reference.height))
    corners = tuple((a * x + b * y + c, d * x + e * y + f) for x, y in pixels)
    if not all(isfinite(value) for corner in corners for value in corner):
        raise ValueError("GeoTIFF world coordinates must be finite")
    return corners


def write_georeferenced_rgb_geotiff(
    rgb: "np.ndarray",
    output_path: str | Path,
    reference: GeoTIFFSpatialReference,
    *,
    georeferencing_verified: bool = False,
) -> Path:
    """Write an RGB GeoTIFF only after upstream georeferencing was verified.

    No preview may be promoted to a georeferenced orthophoto by this writer.
    """
    import numpy as np
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import Affine

    if georeferencing_verified is not True:
        raise ValueError("verified georeferencing is required for GeoTIFF export")
    target = require_geotiff_export_target(output_path, reference)
    if not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint8 or rgb.ndim != 3:
        raise ValueError("GeoTIFF RGB raster must be uint8 HxWx3")
    if rgb.shape != (reference.height, reference.width, 3):
        raise ValueError("GeoTIFF RGB raster dimensions do not match reference")
    if reference.nodata is not None and not 0 <= reference.nodata <= 255:
        raise ValueError("uint8 RGB NoData must be between 0 and 255")
    try:
        crs = CRS.from_user_input(reference.crs)
    except Exception as error:
        raise ValueError("GeoTIFF CRS cannot be parsed") from error
    if crs is None:
        raise ValueError("GeoTIFF CRS cannot be parsed")
    transform = Affine(*reference.transform)
    # Write to a private temporary file, then publish without overwriting.
    import os
    import tempfile

    fd, temporary_name = tempfile.mkstemp(suffix=".tif", prefix=".mcm-geotiff-", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        dataset_context = rasterio.open(
            temporary, "w", driver="GTiff", height=reference.height,
            width=reference.width, count=3, dtype="uint8",
            crs=crs, transform=transform, nodata=reference.nodata,
        )
        with dataset_context as dataset:
            for channel in range(3):
                dataset.write(rgb[:, :, channel], channel + 1)
            dataset.colorinterp = (
                rasterio.enums.ColorInterp.red,
                rasterio.enums.ColorInterp.green,
                rasterio.enums.ColorInterp.blue,
            )
        # Exclusive hard link avoids overwriting a concurrent export.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def inspect_existing_geotiff(path: str | Path) -> GeoTIFFSpatialReference:
    """Read spatial metadata from an existing local GeoTIFF; never infer missing CRS."""
    import rasterio

    source = Path(path)
    if source.suffix.lower() not in (".tif", ".tiff"):
        raise ValueError("Expected a GeoTIFF file")
    try:
        dataset_context = rasterio.open(source)
    except rasterio.errors.RasterioIOError as error:
        raise ValueError("GeoTIFF could not be opened as a GIS raster") from error
    with dataset_context as dataset:
        if dataset.driver != "GTiff" or dataset.crs is None:
            raise ValueError("GeoTIFF must contain a valid CRS")
        reference = GeoTIFFSpatialReference(
            crs=dataset.crs.to_string(),
            transform=tuple(dataset.transform)[:6],
            width=dataset.width,
            height=dataset.height,
            nodata=dataset.nodata,
        )
    validate_geotiff_reference(reference)
    return reference
