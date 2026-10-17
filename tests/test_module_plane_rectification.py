"""Synthetic rectification checks; no claim of field-calibrated DJI accuracy."""
from pathlib import Path
import numpy as np
import pytest

from mcm_solarcheck.domain.models import ImageFrame, Pose
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics, CameraExtrinsicsENU, SurveyedPlane3D
from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid, rectify_module_surface

FRAME = ImageFrame("synthetic", Path("synthetic.jpg"), width=11, height=11,
                   camera_pose=Pose(yaw_deg=0, pitch_deg=-90, roll_deg=0))
CAMERA = VerifiedCameraGeometry(
    PinholeIntrinsics(10, 10, 5, 5),
    CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.))),
    11, 11, "synthetic calibrated", "synthetic frame", "synthetic center", True, True,
)
PLANE = SurveyedPlane3D((0, 0, 0), (0, 0, 1))
GRID = ModuleSurfaceGrid(-0.5, -0.5, 1., 1, 1)


def test_nadir_surface_center_samples_calibrated_image_center():
    image = np.zeros((11, 11, 3), dtype=np.uint8)
    image[5, 5] = (10, 20, 30)
    result = rectify_module_surface(FRAME, image, CAMERA, PLANE, GRID)
    assert result.image.shape == (1, 1, 3)
    np.testing.assert_array_equal(result.image[0, 0], (10, 20, 30))
    assert result.valid_mask[0, 0]
    assert not result.georeferencing_verified
    assert not result.thermal_calibration_verified


def test_thermal_values_are_preserved_without_temperature_claim():
    image = np.full((11, 11), 1400, dtype=np.uint16)
    result = rectify_module_surface(FRAME, image, CAMERA, PLANE, GRID)
    assert result.image.dtype == np.uint16
    assert result.image[0, 0] == 1400
    assert not result.thermal_calibration_verified


def test_reject_unverified_lens_correction_and_oversized_grid():
    from dataclasses import replace
    image = np.zeros((11, 11), dtype=np.uint8)
    with pytest.raises(ValueError, match="lens"):
        rectify_module_surface(FRAME, image, replace(CAMERA, lens_undistortion_verified=False), PLANE, GRID)
    with pytest.raises(ValueError, match="budget"):
        rectify_module_surface(FRAME, image, CAMERA, PLANE, ModuleSurfaceGrid(0, 0, 1, 100, 100), max_pixels=100)


def test_reject_grid_outside_camera_coverage():
    with pytest.raises(ValueError, match="coverage"):
        rectify_module_surface(FRAME, np.zeros((11, 11), dtype=np.uint8), CAMERA, PLANE,
                               ModuleSurfaceGrid(1000, 1000, 1, 1, 1))
