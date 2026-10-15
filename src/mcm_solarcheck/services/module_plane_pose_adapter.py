"""Use already imported DJI pose fields for module geometry diagnostics.

No JPEG/XMP parsing, and no inference of roof slope from gimbal pitch.
"""
from __future__ import annotations

from mcm_solarcheck.domain.models import Pose
from mcm_solarcheck.services.module_plane_geometry_readiness import (
    CameraOrientation, GeometryReadiness, ModulePlane, assess_module_plane_geometry,
)


def camera_orientation_from_imported_pose(pose: Pose) -> CameraOrientation:
    if not isinstance(pose, Pose):
        raise TypeError("imported camera Pose is required")
    return CameraOrientation(
        pitch_deg=pose.pitch_deg,
        roll_deg=pose.roll_deg,
        yaw_deg=pose.yaw_deg,
    )


def assess_imported_pose_for_module(
    pose: Pose, plane: ModulePlane
) -> GeometryReadiness:
    """Check imported gimbal pose and independently established module plane."""
    return assess_module_plane_geometry(
        camera_orientation_from_imported_pose(pose), plane
    )


def assess_imported_frames_for_module(
    frames: tuple[object, ...], plane: ModulePlane
) -> tuple[GeometryReadiness, ...]:
    """Evaluate each imported frame's camera_pose, preserving input order.

    Each frame must expose the existing domain camera_pose attribute.
    """
    results = []
    for frame in frames:
        pose = getattr(frame, "camera_pose", None)
        if not isinstance(pose, Pose):
            raise TypeError("each imported frame must carry a domain camera_pose")
        results.append(assess_imported_pose_for_module(pose, plane))
    return tuple(results)
