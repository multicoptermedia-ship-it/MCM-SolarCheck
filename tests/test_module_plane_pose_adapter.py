"""Imported DJI camera pose feeds geometry gates without re-reading images."""
from mcm_solarcheck.domain.models import Pose
from mcm_solarcheck.services.module_plane_geometry_readiness import ModulePlane
from mcm_solarcheck.services.module_plane_pose_adapter import (
    camera_orientation_from_imported_pose, assess_imported_pose_for_module,
)


def test_imported_gimbal_pose_keeps_pitch_roll_yaw_order():
    pose = Pose(yaw_deg=137, pitch_deg=-63, roll_deg=4)
    camera = camera_orientation_from_imported_pose(pose)
    assert (camera.pitch_deg, camera.roll_deg, camera.yaw_deg) == (-63, 4, 137)


def test_imported_pose_does_not_imply_roof_slope_or_approval():
    pose = Pose(yaw_deg=90, pitch_deg=-65, roll_deg=0)
    incomplete = assess_imported_pose_for_module(pose, ModulePlane(None, None))
    assert not incomplete.metadata_complete
    complete = assess_imported_pose_for_module(
        pose, ModulePlane(25, 180, "survey", "measured")
    )
    assert complete.metadata_complete
    assert not complete.ready_for_reconstruction
