"""Read-only RGB camera incidence diagnostic for an independently surveyed plane.

The angle is measured against the real module/roof-plane normal, not the
vertical ground direction or an uncalibrated DJI gimbal-pitch convention.
The same local ENU geometry used by existing module rectification is reused.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, isfinite
import numpy as np

from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, SurveyedPlane3D,
)


@dataclass(frozen=True)
class RGBPlaneIncidence:
    plane_tilt_from_horizontal_deg: float
    camera_deviation_from_plane_normal_deg: float
    camera_angle_to_module_plane_deg: float
    camera_faces_plane: bool
    perpendicular_target_met: bool
    reflection_review_required: bool = True
    georeferencing_verified: bool = False


def inspect_rgb_plane_incidence(
    camera: CameraExtrinsicsENU,
    plane: SurveyedPlane3D,
    *,
    maximum_deviation_deg: float = 20.0,
) -> RGBPlaneIncidence:
    """Measure incidence only when calibrated local ENU geometry is supplied.

    This is NOT an RTK check, surveyed-control validation or reflection test.
    The maximum deviation is a configurable operational target, not an IEC
    certificate; a near-normal image may reflect the UAV in the glass.
    """
    if not isinstance(camera, CameraExtrinsicsENU) or not isinstance(plane, SurveyedPlane3D):
        raise TypeError("explicit calibrated camera and surveyed plane objects required")
    if type(maximum_deviation_deg) not in (int, float) or not isfinite(maximum_deviation_deg) or not 0 < maximum_deviation_deg < 90:
        raise ValueError("finite positive camera deviation threshold required")
    center = np.asarray(camera.center_enu_m, dtype=float)
    rotation = np.asarray(camera.camera_to_enu, dtype=float)
    origin = np.asarray(plane.point_enu_m, dtype=float)
    normal = np.asarray(plane.normal_enu, dtype=float)
    if (
        center.shape != (3,) or origin.shape != (3,) or normal.shape != (3,)
        or rotation.shape != (3, 3)
        or not all(np.isfinite(v).all() for v in (center, origin, normal, rotation))
    ):
        raise ValueError("finite local ENU geometry required")
    if not np.isclose(np.linalg.norm(normal), 1.0, atol=1e-6):
        raise ValueError("unit normal of surveyed module plane required")
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(rotation), 1, atol=1e-6):
        raise ValueError("proper calibrated camera-to-ENU rotation required")
    if normal[2] < 0:
        raise ValueError("surveyed plane normal must face the upper hemisphere")
    ray = rotation[:, 2]  # Camera z-forward, in ENU.
    signed_cosine = float(ray @ normal)
    viewer_side = float((center - origin) @ normal)
    # Require a forward intersection of the optical axis with this plane.
    facing = signed_cosine < -1e-8 and viewer_side > 0
    angle = degrees(acos(float(np.clip(-signed_cosine, -1., 1.))))
    tilt = degrees(acos(float(np.clip(normal[2], 0., 1.))))
    return RGBPlaneIncidence(
        float(tilt),
        float(angle),
        float(90. - angle),
        bool(facing),
        bool(facing and angle <= maximum_deviation_deg),
    )
