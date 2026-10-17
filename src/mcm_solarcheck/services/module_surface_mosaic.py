"""Conservative multi-frame mosaic on one metric PV-plane grid.

Inputs are already rectified; never fabricate GIS coordinates or temperatures.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid, RectifiedModuleSurface


@dataclass(frozen=True)
class ModuleSurfaceMosaic:
    image: np.ndarray
    valid_mask: np.ndarray
    coverage_fraction: float
    contributor_count: np.ndarray
    grid: ModuleSurfaceGrid
    georeferencing_verified: bool = False
    thermal_calibration_verified: bool = False


def mosaic_rectified_surfaces(
    surfaces: tuple[RectifiedModuleSurface, ...],
    *,
    require_full_coverage: bool = True,
    max_pixels: int = 12_000_000,
) -> ModuleSurfaceMosaic:
    """Use first valid contributor per pixel; do not blend radiometry.

    Ordered input gives deterministic ownership. Thermal raw counts remain raw.
    """
    if not surfaces:
        raise ValueError("at least one rectified surface required")
    first = surfaces[0]
    if not isinstance(first, RectifiedModuleSurface):
        raise TypeError("rectified surface required")
    grid = first.grid
    if type(max_pixels) is not int or max_pixels <= 0 or grid.width * grid.height > max_pixels:
        raise ValueError("mosaic exceeds bounded pixel budget")
    image = np.asarray(first.image)
    if image.ndim not in (2, 3) or image.dtype not in (np.dtype("uint8"), np.dtype("uint16"), np.dtype("float32")):
        raise ValueError("unsupported mosaic raster")
    if not np.isfinite(image).all():
        raise ValueError("nonfinite mosaic raster")
    shape = image.shape
    count = np.zeros((grid.height, grid.width), dtype=np.uint16)
    output = np.zeros_like(image)
    occupied = np.zeros((grid.height, grid.width), dtype=bool)
    for surface in surfaces:
        if not isinstance(surface, RectifiedModuleSurface) or surface.grid != grid:
            raise ValueError("all surfaces must share an identical metric grid")
        raster = np.asarray(surface.image)
        mask = np.asarray(surface.valid_mask)
        if raster.shape != shape or raster.dtype != image.dtype or mask.shape != occupied.shape or mask.dtype != np.dtype("bool"):
            raise ValueError("surface raster or mask mismatch")
        if not np.isfinite(raster).all():
            raise ValueError("nonfinite surface values")
        if surface.georeferencing_verified or surface.thermal_calibration_verified:
            raise ValueError("unsupported verification claims on surface inputs")
        if np.any(mask & (count == np.iinfo(np.uint16).max)):
            raise ValueError("too many overlapping surface contributors")
        count[mask] += 1
        take = mask & ~occupied
        output[take] = raster[take]
        occupied |= mask
    coverage = float(np.count_nonzero(occupied) / occupied.size)
    if require_full_coverage and not occupied.all():
        raise ValueError("incomplete module surface coverage")
    return ModuleSurfaceMosaic(output, occupied, coverage, count, grid)
