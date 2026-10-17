"""Offline module-plane pipeline: surveyed grid -> calibrated rectification -> mosaic.

This produces local metric surface rasters, NOT GIS GeoTIFF orthophotos.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from mcm_solarcheck.domain.models import ImageFrame
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D
from mcm_solarcheck.services.module_surface_grid_planning import plan_surveyed_module_grid
from mcm_solarcheck.services.module_plane_rectification import rectify_module_surface
from mcm_solarcheck.services.module_surface_mosaic import ModuleSurfaceMosaic, mosaic_rectified_surfaces


@dataclass(frozen=True)
class CalibratedSurfaceInput:
    frame: ImageFrame
    undistorted_image: np.ndarray
    geometry: VerifiedCameraGeometry


def build_metric_module_surface(
    frames: tuple[CalibratedSurfaceInput, ...],
    surveyed_corners_enu_m: np.ndarray,
    plane: SurveyedPlane3D,
    *,
    metres_per_pixel: float,
    max_pixels: int = 12_000_000,
    require_full_coverage: bool = True,
) -> ModuleSurfaceMosaic:
    """Use only explicit calibrated undistorted images and surveyed plane data."""
    if not frames:
        raise ValueError("at least one calibrated frame required")
    if any(not isinstance(item, CalibratedSurfaceInput) for item in frames):
        raise TypeError("all frames require explicit calibrated surface inputs")
    identifiers = [item.frame.frame_id for item in frames if isinstance(item.frame, ImageFrame)]
    if len(identifiers) != len(frames) or any(not isinstance(value, str) or not value.strip() for value in identifiers):
        raise ValueError("each surface input needs an imported frame with nonempty ID")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate frame IDs in module surface inputs")
    grid = plan_surveyed_module_grid(
        surveyed_corners_enu_m, plane,
        metres_per_pixel=metres_per_pixel, max_pixels=max_pixels,
    )
    surfaces = tuple(
        rectify_module_surface(item.frame, item.undistorted_image, item.geometry,
                               plane, grid, max_pixels=max_pixels)
        for item in frames
    )
    return mosaic_rectified_surfaces(
        surfaces, require_full_coverage=require_full_coverage, max_pixels=max_pixels,
    )
