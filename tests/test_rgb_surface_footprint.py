"""Calibrated image-footprint proposal is not a verified roof orthophoto."""
from dataclasses import replace
from pathlib import Path
from math import cos, radians, sin

import pytest

from mcm_solarcheck.domain.models import ImageFrame, Pose
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_projection import (
    PinholeIntrinsics, CameraExtrinsicsENU, SurveyedPlane3D,
)
from mcm_solarcheck.services.rgb_surface_footprint import propose_rgb_surface_extent
from mcm_solarcheck.services.rgb_surface_tiles import plan_rgb_surface_tiles

FRAME = ImageFrame("rgb", Path("synthetic.jpg"), width=11, height=11,
                   camera_pose=Pose(yaw_deg=0, pitch_deg=-90, roll_deg=0))
CAMERA = VerifiedCameraGeometry(
    PinholeIntrinsics(10, 10, 5, 5),
    CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.))),
    11, 11, "synthetic camera", "synthetic ENU", "synthetic plane", True, True,
)


def test_surveyed_flat_footprint_can_be_tiled_without_downscaling():
    p = propose_rgb_surface_extent(
        FRAME, CAMERA, SurveyedPlane3D((0, 0, 0), (0, 0, 1)),
        metres_per_pixel=.5,
    )
    assert p.grid.width == 18
    assert p.grid.height == 18
    assert p.grid.u_min_m == pytest.approx(-4.5)
    assert p.grid.v_min_m == pytest.approx(-4.5)
    assert len(p.projected_corners_uv_m) == 4
    assert not p.covers_full_roof
    assert not p.rgb_orthophoto_verified
    assert not p.surveyed_controls_verified
    assert len(plan_rgb_surface_tiles(p.grid, tile_side_px=16).tiles) == 4


def test_sloped_plane_changes_footprint_extent_without_hardcoded_tilt():
    t = radians(30)
    plane = SurveyedPlane3D((0, 0, 0), (sin(t), 0, cos(t)))
    flat = propose_rgb_surface_extent(
        FRAME, CAMERA, SurveyedPlane3D((0, 0, 0), (0, 0, 1)),
        metres_per_pixel=1.,
    )
    inclined = propose_rgb_surface_extent(FRAME, CAMERA, plane, metres_per_pixel=1.)
    assert inclined.projected_corners_uv_m != flat.projected_corners_uv_m


def test_missing_verified_undistortion_and_wrong_dimensions_rejected():
    with pytest.raises(ValueError, match="lens"):
        propose_rgb_surface_extent(
            FRAME, replace(CAMERA, lens_undistortion_verified=False),
            SurveyedPlane3D((0, 0, 0), (0, 0, 1)), metres_per_pixel=1,
        )
    with pytest.raises(ValueError, match="dimensions"):
        propose_rgb_surface_extent(
            replace(FRAME, width=20), CAMERA,
            SurveyedPlane3D((0, 0, 0), (0, 0, 1)), metres_per_pixel=1,
        )


def test_reject_bad_resolution_budget_and_behind_plane():
    horizontal = SurveyedPlane3D((0, 0, 0), (0, 0, 1))
    with pytest.raises(ValueError, match="GSD"):
        propose_rgb_surface_extent(FRAME, CAMERA, horizontal, metres_per_pixel=0)
    with pytest.raises(ValueError, match="budget"):
        propose_rgb_surface_extent(FRAME, CAMERA, horizontal, metres_per_pixel=.01, max_pixels=10)
    with pytest.raises(ValueError, match="behind"):
        propose_rgb_surface_extent(
            FRAME, CAMERA, SurveyedPlane3D((0, 0, 20), (0, 0, 1)),
            metres_per_pixel=1,
        )
