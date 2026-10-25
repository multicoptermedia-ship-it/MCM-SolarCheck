"""Read-only RGB tile rendering on an explicitly calibrated true plane.

Delegates all camera/pixel geometry to the EXISTING rectify_module_surface
service. Empty frame coverage is represented by a blank mask, never filled in
or reported as a successful roof reconstruction.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from mcm_solarcheck.domain.models import ImageFrame
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D
from mcm_solarcheck.services.module_plane_rectification import rectify_module_surface
from mcm_solarcheck.services.rgb_surface_tiles import RGBSurfaceTile


@dataclass(frozen=True)
class RGBRenderedSurfaceTile:
    tile: RGBSurfaceTile
    bgr: np.ndarray
    valid_mask: np.ndarray
    covered_pixels: int
    status: str = "unverified_local_plane_preview"
    georeferencing_verified: bool = False


def render_rgb_surface_tile(
    frame: ImageFrame,
    undistorted_bgr: np.ndarray,
    geometry: VerifiedCameraGeometry,
    plane: SurveyedPlane3D,
    tile: RGBSurfaceTile,
) -> RGBRenderedSurfaceTile:
    """Render only one bounded RGB tile, preserving the caller's source."""
    if not isinstance(tile, RGBSurfaceTile):
        raise TypeError("explicit planned metric tile required")
    g = tile.grid
    if (
        type(g.width) is not int or type(g.height) is not int
        or g.width < 1 or g.height < 1
        or g.width > 2048 or g.height > 2048
    ):
        raise ValueError("tile dimensions outside bounded RGB preview limit")
    if (
        not isinstance(undistorted_bgr, np.ndarray)
        or undistorted_bgr.ndim != 3 or undistorted_bgr.shape[2] != 3
        or undistorted_bgr.dtype != np.uint8
    ):
        raise ValueError("undistorted RGB source must be BGR uint8 HxWx3")
    try:
        result = rectify_module_surface(
            frame, undistorted_bgr, geometry, plane, g, max_pixels=2048 * 2048,
        )
    except ValueError as exc:
        if str(exc) != "surface grid has no visible image coverage":
            raise
        black = np.zeros((g.height, g.width, 3), dtype=np.uint8)
        mask = np.zeros((g.height, g.width), dtype=bool)
        return RGBRenderedSurfaceTile(tile, black, mask, 0)
    return RGBRenderedSurfaceTile(
        tile, result.image, result.valid_mask,
        int(np.count_nonzero(result.valid_mask)),
    )
