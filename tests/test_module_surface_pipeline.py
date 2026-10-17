"""End-to-end synthetic tests for local metric PV module surface pipeline."""
from pathlib import Path
from dataclasses import replace
import numpy as np
import pytest

from mcm_solarcheck.domain.models import ImageFrame, Pose
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_projection import CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D
from mcm_solarcheck.services.module_surface_pipeline import CalibratedSurfaceInput, build_metric_module_surface

PLANE = SurveyedPlane3D((0, 0, 0), (0, 0, 1))
CORNERS = np.array([[-0.5, -0.5, 0], [0.5, -0.5, 0], [0.5, 0.5, 0], [-0.5, 0.5, 0]])
FRAME = ImageFrame("synthetic", Path("synthetic.jpg"), width=11, height=11,
                   camera_pose=Pose(yaw_deg=0, pitch_deg=-90, roll_deg=0))
GEOMETRY = VerifiedCameraGeometry(
    PinholeIntrinsics(10, 10, 5, 5),
    CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.))),
    11, 11, "synthetic calibration", "synthetic ENU rotation", "synthetic survey", True, True,
)


def test_surveyed_surface_pipeline_builds_mosaic_from_two_calibrated_frames():
    a = CalibratedSurfaceInput(FRAME, np.full((11, 11), 10, dtype=np.uint16), GEOMETRY)
    b = CalibratedSurfaceInput(replace(FRAME, frame_id="second"), np.full((11, 11), 20, dtype=np.uint16), GEOMETRY)
    mosaic = build_metric_module_surface((a, b), CORNERS, PLANE, metres_per_pixel=0.5)
    assert mosaic.image.shape == (2, 2)
    np.testing.assert_array_equal(mosaic.image, np.full((2, 2), 10))
    np.testing.assert_array_equal(mosaic.contributor_count, np.full((2, 2), 2))
    assert mosaic.coverage_fraction == 1.0
    assert not mosaic.georeferencing_verified
    assert not mosaic.thermal_calibration_verified


def test_pipeline_rejects_unverified_calibration():
    bad = replace(GEOMETRY, reference_frames_verified=False)
    with pytest.raises(ValueError, match="reference-frame"):
        build_metric_module_surface(
            (CalibratedSurfaceInput(FRAME, np.zeros((11, 11), dtype=np.uint8), bad),),
            CORNERS, PLANE, metres_per_pixel=0.5,
        )


def test_pipeline_rejects_unbounded_raster():
    with pytest.raises(ValueError, match="budget"):
        build_metric_module_surface(
            (CalibratedSurfaceInput(FRAME, np.zeros((11, 11), dtype=np.uint8), GEOMETRY),),
            CORNERS, PLANE, metres_per_pixel=0.001, max_pixels=100,
        )
