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
