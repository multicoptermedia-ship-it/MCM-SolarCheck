"""Explicit calibrated pinhole-ray intersection with a surveyed 3D PV plane.

Local metric ENU coordinates (east, north, up); camera-to-world rotation
maps camera x-right, y-down, z-forward rays into ENU. No DJI angle convention
is inferred here. Outputs are 3D points on the declared plane, not GeoTIFFs.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class PinholeIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float


@dataclass(frozen=True)
class SurveyedPlane3D:
    point_enu_m: tuple[float, float, float]
    normal_enu: tuple[float, float, float]


@dataclass(frozen=True)
class CameraExtrinsicsENU:
    center_enu_m: tuple[float, float, float]
    camera_to_enu: tuple[tuple[float, float, float], ...]


def project_pixels_to_surveyed_plane(
    pixels_xy: np.ndarray,
    intrinsics: PinholeIntrinsics,
    extrinsics: CameraExtrinsicsENU,
    plane: SurveyedPlane3D,
) -> np.ndarray:
    """Intersect undistorted image pixels with plane; reject invalid/behind rays.

    Requires independently calibrated intrinsics, rotation and plane inputs.
    Caller must have already corrected lens distortion and reference frames.
    """
    pixels = np.asarray(pixels_xy, dtype=np.float64)
    if pixels.ndim != 2 or pixels.shape[1] != 2 or not len(pixels) or not np.isfinite(pixels).all():
        raise ValueError("pixels must be a nonempty finite Nx2 array")
    k = np.array([intrinsics.fx, intrinsics.fy, intrinsics.cx, intrinsics.cy], dtype=np.float64)
    if not np.isfinite(k).all() or np.any(k[:2] <= 0):
        raise ValueError("finite positive focal lengths and principal point required")
    center = np.asarray(extrinsics.center_enu_m, dtype=np.float64)
    rotation = np.asarray(extrinsics.camera_to_enu, dtype=np.float64)
    point = np.asarray(plane.point_enu_m, dtype=np.float64)
    normal = np.asarray(plane.normal_enu, dtype=np.float64)
    if center.shape != (3,) or point.shape != (3,) or normal.shape != (3,) or rotation.shape != (3, 3):
        raise ValueError("invalid ENU camera or plane dimensions")
    if not all(np.isfinite(a).all() for a in (center, point, normal, rotation)):
        raise ValueError("nonfinite camera or plane geometry")
    if not np.isclose(np.linalg.norm(normal), 1.0, atol=1e-6):
        raise ValueError("plane normal must be unit length")
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(rotation), 1.0, atol=1e-6):
        raise ValueError("camera-to-ENU rotation must be proper orthonormal")
    camera_rays = np.column_stack(((pixels[:, 0] - k[2]) / k[0], (pixels[:, 1] - k[3]) / k[1], np.ones(len(pixels))))
    rays = camera_rays @ rotation.T
    denominators = rays @ normal
    if np.any(np.abs(denominators) < 1e-10):
        raise ValueError("camera rays parallel to module plane")
    distances = ((point - center) @ normal) / denominators
    if np.any(~np.isfinite(distances)) or np.any(distances <= 0):
        raise ValueError("module plane lies behind camera or on camera center")
    return center + distances[:, None] * rays
