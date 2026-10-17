"""Independent surveyed-control reprojection audit for calibrated PV-plane geometry.

Control points are held-out observations, not fitted or used to create a pose.
All ENU coordinates are local metric; this is not a GIS accuracy certificate.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D,
    project_pixels_to_surveyed_plane,
)


@dataclass(frozen=True)
class PlaneControlAudit:
    count: int
    rms_error_m: float
    max_error_m: float
    tolerance_m: float
    within_tolerance: bool
    independently_verified: bool = False


def audit_surveyed_plane_controls(
    image_pixels_xy: np.ndarray,
    surveyed_points_enu_m: np.ndarray,
    intrinsics: PinholeIntrinsics,
    extrinsics: CameraExtrinsicsENU,
    plane: SurveyedPlane3D,
    *,
    tolerance_m: float,
) -> PlaneControlAudit:
    """Compare predicted 3D intersections against independently surveyed controls.

    At least four distinct points spanning two surface directions are required.
    This cannot establish independent verification without provenance evidence.
    """
    pixels = np.asarray(image_pixels_xy, dtype=np.float64)
    surveyed = np.asarray(surveyed_points_enu_m, dtype=np.float64)
    if surveyed.ndim != 2 or surveyed.shape[1] != 3 or surveyed.shape[0] < 4:
        raise ValueError("at least four surveyed 3D controls required")
    if pixels.shape != (len(surveyed), 2) or not np.isfinite(surveyed).all():
        raise ValueError("matched finite surveyed 3D controls required")
    if not isinstance(tolerance_m, (int, float)) or not np.isfinite(tolerance_m) or tolerance_m <= 0:
        raise ValueError("finite positive metric tolerance required")
    if not np.isfinite(pixels).all() or len(np.unique(pixels, axis=0)) < 4 or len(np.unique(surveyed, axis=0)) < 4:
        raise ValueError("finite distinct image and surveyed controls required")
    centered = surveyed - surveyed.mean(axis=0)
    singular = np.linalg.svd(centered, compute_uv=False)
    if singular[0] <= 0 or singular[1] / singular[0] < 1e-6:
        raise ValueError("surveyed controls must span two surface directions")
    point = np.asarray(plane.point_enu_m, dtype=np.float64)
    normal = np.asarray(plane.normal_enu, dtype=np.float64)
    if point.shape != (3,) or normal.shape != (3,) or not np.isfinite(point).all() or not np.isfinite(normal).all():
        raise ValueError("finite plane geometry required")
    if not np.isclose(np.linalg.norm(normal), 1.0, atol=1e-6):
        raise ValueError("unit plane normal required")
    if np.max(np.abs((surveyed - point) @ normal)) > tolerance_m:
        raise ValueError("surveyed controls do not lie on declared module plane")
    predicted = project_pixels_to_surveyed_plane(pixels, intrinsics, extrinsics, plane)
    errors = np.linalg.norm(predicted - surveyed, axis=1)
    rms = float(np.sqrt(np.mean(errors ** 2)))
    maximum = float(np.max(errors))
    return PlaneControlAudit(len(errors), rms, maximum, float(tolerance_m), maximum <= tolerance_m)
