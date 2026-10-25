"""Estimate a local metric roof-plane *candidate extent* from a verified camera.

The projected photo corners bound the camera frustum's intersection with one
declared plane. This does not certify coverage, surface truth, GSD, overlap,
occlusion, multi-roof reconstruction or GIS georeferencing.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
import numpy as np

from mcm_solarcheck.domain.models import ImageFrame
from mcm_solarcheck.services.module_camera_calibration_gate import (
    VerifiedCameraGeometry, require_verified_camera_geometry,
)
from mcm_solarcheck.services.module_plane_basis import (
    project_image_pixels_to_plane_coordinates,
)
from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D
from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid


@dataclass(frozen=True)
class RGBSurfaceFootprintPlan:
    grid: ModuleSurfaceGrid
    projected_corners_uv_m: tuple[tuple[float, float], ...]
    covers_full_roof: bool = False
    surveyed_controls_verified: bool = False
    rgb_orthophoto_verified: bool = False


def propose_rgb_surface_extent(
    frame: ImageFrame,
    geometry: VerifiedCameraGeometry,
    plane: SurveyedPlane3D,
    *,
    metres_per_pixel: float,
    padding_m: float = 0.,
    max_pixels: int = 40_000_000,
) -> RGBSurfaceFootprintPlan:
    """Project undistorted IMAGE boundaries to an existing surveyed plane."""
    require_verified_camera_geometry(frame, geometry)
    if (
        type(metres_per_pixel) not in (float, int)
        or not isfinite(metres_per_pixel) or metres_per_pixel <= 0
        or type(padding_m) not in (float, int)
        or not isfinite(padding_m) or padding_m < 0
        or type(max_pixels) is not int or max_pixels <= 0
    ):
        raise ValueError("finite positive GSD and bounded extent budget required")
    width, height = geometry.image_width, geometry.image_height
    if width < 2 or height < 2:
        raise ValueError("at least 2x2 undistorted pixels required")
    xy = np.asarray([
        [0.5, 0.5], [width - 1.5, 0.5],
        [width - 1.5, height - 1.5], [0.5, height - 1.5],
    ], dtype=float)
    projected = project_image_pixels_to_plane_coordinates(
        xy, geometry.intrinsics, geometry.extrinsics, plane,
    )
    lower = projected.min(axis=0) - padding_m
    upper = projected.max(axis=0) + padding_m
    dimensions = np.ceil((upper - lower) / metres_per_pixel).astype(np.int64)
    if np.any(dimensions <= 0) or np.any(dimensions > 100_000) or int(dimensions[0]) * int(dimensions[1]) > max_pixels:
        raise ValueError("projected roof plane extent exceeds bounded pixel budget")
    grid = ModuleSurfaceGrid(
        float(lower[0]), float(lower[1]), float(metres_per_pixel),
        int(dimensions[0]), int(dimensions[1]),
    )
    return RGBSurfaceFootprintPlan(
        grid, tuple((float(u), float(v)) for u, v in projected),
    )
