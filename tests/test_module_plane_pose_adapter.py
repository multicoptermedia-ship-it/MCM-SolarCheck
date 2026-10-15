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


def test_imported_frame_batch_preserves_order_and_rejects_missing_pose():
    from types import SimpleNamespace
    import pytest
    from mcm_solarcheck.services.module_plane_pose_adapter import (
        assess_imported_frames_for_module,
    )
    frames = (
        SimpleNamespace(camera_pose=Pose(yaw_deg=30, pitch_deg=-80, roll_deg=0)),
        SimpleNamespace(camera_pose=Pose(yaw_deg=30, pitch_deg=None, roll_deg=0)),
    )
    plane = ModulePlane(25, 180, "survey", "measured")
    results = assess_imported_frames_for_module(frames, plane)
    assert len(results) == 2
    assert results[0].metadata_complete
    assert not results[1].metadata_complete
    assert not any(result.ready_for_reconstruction for result in results)
    with pytest.raises(TypeError, match="camera_pose"):
        assess_imported_frames_for_module((SimpleNamespace(),), plane)
