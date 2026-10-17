"""Inverse-map a calibrated image onto a bounded metric PV module plane grid.

Local surface raster only: not a geographic orthophoto or verified survey output.
Input image must already be undistorted. No DJI angle convention is inferred.
"""
from __future__ import annotations

from dataclasses import dataclass
import cv2
import numpy as np

from mcm_solarcheck.services.module_camera_calibration_gate import (
    VerifiedCameraGeometry, require_verified_camera_geometry,
)
from mcm_solarcheck.services.module_plane_basis import basis_from_surveyed_plane
from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D
from mcm_solarcheck.domain.models import ImageFrame


@dataclass(frozen=True)
class ModuleSurfaceGrid:
    u_min_m: float
    v_min_m: float
    metres_per_pixel: float
    width: int
    height: int


@dataclass(frozen=True)
class RectifiedModuleSurface:
    image: np.ndarray
    valid_mask: np.ndarray
    grid: ModuleSurfaceGrid
    georeferencing_verified: bool = False
    thermal_calibration_verified: bool = False


def rectify_module_surface(
    frame: ImageFrame,
    undistorted_image: np.ndarray,
    geometry: VerifiedCameraGeometry,
    plane: SurveyedPlane3D,
    grid: ModuleSurfaceGrid,
    *,
    max_pixels: int = 12_000_000,
) -> RectifiedModuleSurface:
    """Sample surface pixel centres using an explicitly supplied calibrated camera."""
    require_verified_camera_geometry(frame, geometry)
    if not isinstance(grid, ModuleSurfaceGrid):
        raise TypeError("explicit metric surface grid required")
    values = (grid.u_min_m, grid.v_min_m, grid.metres_per_pixel)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and np.isfinite(v) for v in values):
        raise ValueError("finite metric surface grid required")
    if grid.metres_per_pixel <= 0 or any(type(v) is not int or v <= 0 for v in (grid.width, grid.height)):
        raise ValueError("positive surface grid resolution and dimensions required")
    if type(max_pixels) is not int or max_pixels <= 0 or grid.width * grid.height > max_pixels:
        raise ValueError("surface grid exceeds bounded pixel budget")
    image = np.asarray(undistorted_image)
    if image.ndim not in (2, 3) or image.shape[:2] != (geometry.image_height, geometry.image_width):
        raise ValueError("undistorted image dimensions do not match calibration")
    if image.ndim == 3 and image.shape[2] not in (3, 4):
        raise ValueError("unsupported image channel count")
    if image.dtype not in (np.dtype("uint8"), np.dtype("uint16"), np.dtype("float32")):
        raise ValueError("unsupported source raster type")
    if not np.isfinite(image).all():
        raise ValueError("source raster contains nonfinite values")
    basis = basis_from_surveyed_plane(plane)
    origin = np.asarray(basis.origin_enu_m)
    u = np.asarray(basis.axis_u_enu)
    v = np.asarray(basis.axis_v_enu)
    xs = grid.u_min_m + (np.arange(grid.width) + 0.5) * grid.metres_per_pixel
    ys = grid.v_min_m + (np.arange(grid.height) + 0.5) * grid.metres_per_pixel
    uu, vv = np.meshgrid(xs, ys)
    world = origin + uu[..., None] * u + vv[..., None] * v
    center = np.asarray(geometry.extrinsics.center_enu_m)
    rotation = np.asarray(geometry.extrinsics.camera_to_enu)
    camera = (world - center) @ rotation
    z = camera[..., 2]
    front = z > 1e-9
    safe_z = np.where(front, z, 1.)
    k = geometry.intrinsics
    px = k.fx * camera[..., 0] / safe_z + k.cx
    py = k.fy * camera[..., 1] / safe_z + k.cy
    valid = front & (px >= 0) & (py >= 0) & (px < image.shape[1] - 1) & (py < image.shape[0] - 1)
    if not np.isfinite(px).all() or not np.isfinite(py).all():
        raise ValueError("nonfinite projection to camera raster")
    if not np.any(valid):
        raise ValueError("surface grid has no visible image coverage")
    map_x = np.where(valid, px, -1).astype(np.float32)
    map_y = np.where(valid, py, -1).astype(np.float32)
    output = cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return RectifiedModuleSurface(output, valid, grid)
