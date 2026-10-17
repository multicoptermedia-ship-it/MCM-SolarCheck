"""Fail-closed bridge from imported DJI frames to explicitly verified camera inputs.

No XMP reread, Euler-angle conversion, roof-tilt inference or implicit calibration.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from mcm_solarcheck.domain.models import ImageFrame, Pose
from mcm_solarcheck.services.module_plane_projection import CameraExtrinsicsENU, PinholeIntrinsics


@dataclass(frozen=True)
class VerifiedCameraGeometry:
    intrinsics: PinholeIntrinsics
    extrinsics: CameraExtrinsicsENU
    image_width: int
    image_height: int
    calibration_provenance: str
    rotation_provenance: str
    survey_provenance: str
    lens_undistortion_verified: bool = False
    reference_frames_verified: bool = False


def require_verified_camera_geometry(frame: ImageFrame, geometry: VerifiedCameraGeometry) -> VerifiedCameraGeometry:
    """Validate independently supplied geometry against an already imported frame.

    This does NOT derive ENU rotation from DJI gimbal angles or claim accuracy.
    """
    if not isinstance(frame, ImageFrame) or not isinstance(frame.camera_pose, Pose):
        raise TypeError("existing imported ImageFrame with camera_pose required")
    angles = (frame.camera_pose.pitch_deg, frame.camera_pose.roll_deg, frame.camera_pose.yaw_deg)
    if any(v is None or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in angles):
        raise ValueError("complete finite imported DJI camera pose required")
    if not isinstance(geometry, VerifiedCameraGeometry):
        raise TypeError("explicit verified camera geometry required")
    if geometry.lens_undistortion_verified is not True or geometry.reference_frames_verified is not True:
        raise ValueError("lens correction and reference-frame conventions must be verified")
    if not all(isinstance(v, str) and v.strip() for v in (
        geometry.calibration_provenance, geometry.rotation_provenance, geometry.survey_provenance
    )):
        raise ValueError("calibration, rotation and survey provenance required")
    if any(type(v) is not int or v <= 0 for v in (geometry.image_width, geometry.image_height)):
        raise ValueError("positive image dimensions required")
    if (frame.width is not None and frame.width != geometry.image_width) or (
        frame.height is not None and frame.height != geometry.image_height
    ):
        raise ValueError("camera calibration dimensions mismatch imported frame")
    k = geometry.intrinsics
    if not all(not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) for v in (k.fx, k.fy, k.cx, k.cy)):
        raise ValueError("finite calibrated intrinsics required")
    if k.fx <= 0 or k.fy <= 0 or not (0 <= k.cx < geometry.image_width and 0 <= k.cy < geometry.image_height):
        raise ValueError("calibrated intrinsics outside image bounds")
    import numpy as np
    rotation = np.asarray(geometry.extrinsics.camera_to_enu, dtype=float)
    center = np.asarray(geometry.extrinsics.center_enu_m, dtype=float)
    if rotation.shape != (3, 3) or center.shape != (3,) or not np.isfinite(rotation).all() or not np.isfinite(center).all():
        raise ValueError("finite 3D camera extrinsics required")
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(rotation), 1, atol=1e-6):
        raise ValueError("proper camera-to-ENU rotation required")
    return geometry
