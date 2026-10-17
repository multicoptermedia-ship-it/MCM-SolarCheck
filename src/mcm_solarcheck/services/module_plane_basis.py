"""Construct a deterministic metric coordinate basis for a surveyed PV plane.

ENU is east/north/up. Coordinates are local metres, not a GIS CRS.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D


@dataclass(frozen=True)
class PlaneBasisENU:
    origin_enu_m: tuple[float, float, float]
    axis_u_enu: tuple[float, float, float]
    axis_v_enu: tuple[float, float, float]


def basis_from_surveyed_plane(plane: SurveyedPlane3D) -> PlaneBasisENU:
    """Choose an in-plane u-axis toward projected east, v = normal cross u."""
    point = np.asarray(plane.point_enu_m, dtype=np.float64)
    normal = np.asarray(plane.normal_enu, dtype=np.float64)
    if point.shape != (3,) or normal.shape != (3,) or not np.isfinite(point).all() or not np.isfinite(normal).all():
        raise ValueError("finite ENU plane point and normal required")
    if not np.isclose(np.linalg.norm(normal), 1.0, atol=1e-6):
        raise ValueError("unit plane normal required")
    east = np.array([1., 0., 0.])
    u = east - np.dot(east, normal) * normal
    if np.linalg.norm(u) < 1e-8:
        north = np.array([0., 1., 0.])
        u = north - np.dot(north, normal) * normal
    u /= np.linalg.norm(u)
    v = np.cross(normal, u)
    return PlaneBasisENU(tuple(point), tuple(u), tuple(v))


def plane_coordinates(points_enu_m: np.ndarray, basis: PlaneBasisENU, *, tolerance_m: float = 1e-5) -> np.ndarray:
    """Map 3D points already on the surveyed plane to local metric (u,v)."""
    points = np.asarray(points_enu_m, dtype=np.float64)
    origin = np.asarray(basis.origin_enu_m, dtype=np.float64)
    u = np.asarray(basis.axis_u_enu, dtype=np.float64)
    v = np.asarray(basis.axis_v_enu, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points) or not np.isfinite(points).all():
        raise ValueError("finite nonempty Nx3 ENU points required")
    if origin.shape != (3,) or u.shape != (3,) or v.shape != (3,) or not all(np.isfinite(a).all() for a in (origin,u,v)):
        raise ValueError("finite basis vectors required")
    if not np.allclose([u @ u, v @ v, u @ v], [1., 1., 0.], atol=1e-6):
        raise ValueError("orthonormal basis required")
    if not np.isfinite(tolerance_m) or tolerance_m < 0:
        raise ValueError("finite nonnegative plane tolerance required")
    offsets = points - origin
    residual = offsets - (offsets @ u)[:, None] * u - (offsets @ v)[:, None] * v
    if np.any(np.linalg.norm(residual, axis=1) > tolerance_m):
        raise ValueError("points are not on the surveyed plane")
    return np.column_stack((offsets @ u, offsets @ v))


def project_image_pixels_to_plane_coordinates(
    pixels_xy: np.ndarray,
    intrinsics: "PinholeIntrinsics",
    extrinsics: "CameraExtrinsicsENU",
    plane: SurveyedPlane3D,
) -> np.ndarray:
    """Return local metric plane coordinates from calibrated undistorted pixels.

    The local origin is the surveyed plane point; no map CRS is implied.
    """
    from mcm_solarcheck.services.module_plane_projection import project_pixels_to_surveyed_plane
    world_points = project_pixels_to_surveyed_plane(pixels_xy, intrinsics, extrinsics, plane)
    return plane_coordinates(world_points, basis_from_surveyed_plane(plane))
