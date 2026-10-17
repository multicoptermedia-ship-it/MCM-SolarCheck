"""Plan a bounded metric raster from independently surveyed PV-plane corners.

No DJI pose inference and no GIS CRS is assigned to the local surface grid.
"""
from __future__ import annotations

import math
import numpy as np

from mcm_solarcheck.services.module_plane_basis import basis_from_surveyed_plane, plane_coordinates
from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D
from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid


def plan_surveyed_module_grid(
    corners_enu_m: np.ndarray,
    plane: SurveyedPlane3D,
    *,
    metres_per_pixel: float,
    max_pixels: int = 12_000_000,
    plane_tolerance_m: float = 0.01,
) -> ModuleSurfaceGrid:
    """Enclose surveyed surface corners; pixel centres cover their metric bounds."""
    if not isinstance(metres_per_pixel, (int, float)) or isinstance(metres_per_pixel, bool) or not math.isfinite(metres_per_pixel) or metres_per_pixel <= 0:
        raise ValueError("positive finite metric resolution required")
    if type(max_pixels) is not int or max_pixels <= 0:
        raise ValueError("positive integer pixel budget required")
    corners = np.asarray(corners_enu_m, dtype=np.float64)
    if corners.ndim != 2 or corners.shape[1] != 3 or len(corners) < 3 or not np.isfinite(corners).all():
        raise ValueError("at least three finite surveyed ENU corners required")
    uv = plane_coordinates(corners, basis_from_surveyed_plane(plane), tolerance_m=plane_tolerance_m)
    centered = uv - uv.mean(axis=0)
    singular = np.linalg.svd(centered, compute_uv=False)
    if len(np.unique(uv, axis=0)) < 3 or singular[0] <= 0 or singular[1] / singular[0] < 1e-6:
        raise ValueError("surveyed corners must span a nondegenerate module area")
    lower = uv.min(axis=0)
    upper = uv.max(axis=0)
    extent = upper - lower
    width = max(1, math.ceil(float(extent[0]) / metres_per_pixel))
    height = max(1, math.ceil(float(extent[1]) / metres_per_pixel))
    if width * height > max_pixels:
        raise ValueError("planned module grid exceeds pixel budget")
    return ModuleSurfaceGrid(float(lower[0]), float(lower[1]), float(metres_per_pixel), width, height)
