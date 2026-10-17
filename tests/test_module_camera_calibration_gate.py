"""No unverified DJI angle conversion or synthetic camera approval."""
from dataclasses import replace
import pytest

from mcm_solarcheck.domain.models import ImageFrame, Pose
from mcm_solarcheck.services.module_camera_calibration_gate import (
    VerifiedCameraGeometry, require_verified_camera_geometry,
)
from mcm_solarcheck.services.module_plane_projection import CameraExtrinsicsENU, PinholeIntrinsics

FRAME = ImageFrame("test", __import__("pathlib").Path("not-a-real-image.jpg"), width=4000, height=3000,
                   camera_pose=Pose(yaw_deg=130, pitch_deg=-65, roll_deg=2))
GEOMETRY = VerifiedCameraGeometry(
    PinholeIntrinsics(2000, 2000, 2000, 1500),
    CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.))),
    4000, 3000, "independent lens calibration", "independent frame validation",
    "independent surveyed center", True, True,
)


def test_verified_inputs_preserve_existing_pose_without_converting_angles():
    assert require_verified_camera_geometry(FRAME, GEOMETRY) is GEOMETRY


@pytest.mark.parametrize("geometry", [
    replace(GEOMETRY, lens_undistortion_verified=False),
    replace(GEOMETRY, reference_frames_verified=False),
    replace(GEOMETRY, rotation_provenance=""),
    replace(GEOMETRY, image_width=640),
    replace(GEOMETRY, intrinsics=PinholeIntrinsics(0, 2000, 2000, 1500)),
])
def test_unverified_or_mismatched_calibration_is_rejected(geometry):
    with pytest.raises(ValueError):
        require_verified_camera_geometry(FRAME, geometry)


def test_missing_imported_gimbal_pose_is_rejected():
    with pytest.raises(ValueError, match="pose"):
        require_verified_camera_geometry(replace(FRAME, camera_pose=Pose()), GEOMETRY)


def test_boolean_angles_and_focal_lengths_are_not_calibration():
    with pytest.raises(ValueError, match="pose"):
        require_verified_camera_geometry(replace(FRAME, camera_pose=Pose(yaw_deg=True, pitch_deg=-65, roll_deg=2)), GEOMETRY)
    with pytest.raises(ValueError, match="intrinsics"):
        require_verified_camera_geometry(FRAME, replace(GEOMETRY, intrinsics=PinholeIntrinsics(True, 2000, 2000, 1500)))


def test_nonrotation_is_rejected():
    bad = replace(GEOMETRY, extrinsics=CameraExtrinsicsENU((0, 0, 10), ((2., 0., 0.), (0., -1., 0.), (0., 0., -1.))))
    with pytest.raises(ValueError, match="rotation"):
        require_verified_camera_geometry(FRAME, bad)
