"""Camera gimbal angles cannot stand in for module surface geometry."""
import math
import pytest

from mcm_solarcheck.services.module_plane_geometry_readiness import (
    CameraOrientation, ModulePlane, assess_module_plane_geometry,
)


def test_complete_independent_angles_are_not_automatic_reconstruction_approval():
    result = assess_module_plane_geometry(
        CameraOrientation(-70, 0, 135),
        ModulePlane(25, 180, provenance="surveyed roof plane", confidence="surveyed"),
    )
    assert result.metadata_complete
    assert not result.ready_for_reconstruction
    assert "calibration" in result.diagnostics[0]


@pytest.mark.parametrize("pose", [
    CameraOrientation(None, 0, 0),
    CameraOrientation(float("nan"), 0, 0),
    CameraOrientation(0, float("inf"), 0),
    CameraOrientation(0, 0, None),
])
def test_missing_or_nonfinite_camera_orientation_is_not_ready(pose):
    result = assess_module_plane_geometry(
        pose, ModulePlane(25, 180, "survey", "measured")
    )
    assert not result.metadata_complete
    assert not result.ready_for_reconstruction


def test_camera_pitch_does_not_supply_module_tilt_or_provenance():
    result = assess_module_plane_geometry(
        CameraOrientation(-65, 0, 0), ModulePlane(None, None)
    )
    assert not result.metadata_complete
    assert any("tilt" in d for d in result.diagnostics)
    assert any("azimuth" in d for d in result.diagnostics)
    assert any("provenance" in d for d in result.diagnostics)
