import pytest

from mcm_solarcheck.domain.models import Pose
from mcm_solarcheck.services.orthomosaic_geometry import (
    CameraOrientation, ModulePlane, assess_geometry_readiness,
)
from mcm_solarcheck.services.orthomosaic_reconstruction_plan import (
    plan_module_plane_reconstruction,
)


def pose(pitch=-89.9):
    return Pose(yaw_deg=23.8, pitch_deg=pitch, roll_deg=0.0)


def plane():
    return ModulePlane("roof-east", 27.0, 145.0, "surveyed")


def test_camera_metadata_does_not_imply_perpendicular_incidence():
    ready = assess_geometry_readiness(plane(), (pose(), pose(-88.0)))
    assert ready.ready_for_reconstruction_attempt
    assert len(ready.cameras) == 2
    assert "unverified" in ready.notes[0]


def test_missing_pose_fails_closed():
    missing = Pose(yaw_deg=None, pitch_deg=-89.9, roll_deg=0.0)
    assert not assess_geometry_readiness(plane(), (missing,)).ready_for_reconstruction_attempt
    with pytest.raises(ValueError):
        plan_module_plane_reconstruction("p", plane(), ("v1",), ("t1",), (missing,))


@pytest.mark.parametrize("tilt,azimuth", [(-1, 20), (91, 20), (20, 360), (float("nan"), 20)])
def test_invalid_plane(tilt, azimuth):
    with pytest.raises(ValueError):
        ModulePlane("p", tilt, azimuth, "survey")


def test_paired_plan_and_rejections():
    plan = plan_module_plane_reconstruction("p", plane(), ("v1", "v2"), ("t1", "t2"), (pose(), pose()))
    assert plan.view == "module_plane"
    with pytest.raises(ValueError):
        plan_module_plane_reconstruction("p", plane(), ("v1",), ("t1", "t2"), (pose(),))
    with pytest.raises(ValueError):
        CameraOrientation.from_dji_pose(Pose(yaw_deg=0, pitch_deg=float("nan"), roll_deg=0))
