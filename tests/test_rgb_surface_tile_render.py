"""Synthetic local RGB roof tile rendering; no client photos and no file writes."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from mcm_solarcheck.domain.models import ImageFrame, Pose
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D,
)
from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid
from mcm_solarcheck.services.rgb_surface_tile_render import render_rgb_surface_tile
from mcm_solarcheck.services.rgb_surface_tiles import RGBSurfaceTile

FRAME = ImageFrame("one", Path("synthetic.jpg"), width=11, height=11,
                   camera_pose=Pose(yaw_deg=0, pitch_deg=-90, roll_deg=0))
GEOMETRY = VerifiedCameraGeometry(
    PinholeIntrinsics(10, 10, 5, 5),
    CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.))),
    11, 11, "synthetic calibration", "synthetic rotation", "synthetic survey", True, True,
)
PLANE = SurveyedPlane3D((0, 0, 0), (0, 0, 1))
TILE = RGBSurfaceTile(0, 0, ModuleSurfaceGrid(-.5, -.5, 1, 1, 1))


def test_render_follows_actual_metric_plane_and_does_not_mutate_input():
    src = np.zeros((11, 11, 3), dtype=np.uint8)
    src[5, 5] = (12, 34, 56)
    before = src.copy()
    result = render_rgb_surface_tile(FRAME, src, GEOMETRY, PLANE, TILE)
    np.testing.assert_array_equal(src, before)
    assert result.bgr.shape == (1, 1, 3)
    np.testing.assert_array_equal(result.bgr[0, 0], (12, 34, 56))
    assert result.covered_pixels == 1
    assert result.valid_mask[0, 0]
    assert result.status == "unverified_local_plane_preview"
    assert not result.georeferencing_verified


def test_no_coverage_is_reported_as_masked_not_fabricated_roof_pixels():
    src = np.ones((11, 11, 3), dtype=np.uint8) * 99
    far = RGBSurfaceTile(0, 0, ModuleSurfaceGrid(10_000, 10_000, 1, 2, 2))
    result = render_rgb_surface_tile(FRAME, src, GEOMETRY, PLANE, far)
    assert result.covered_pixels == 0
    assert not result.valid_mask.any()
    assert result.bgr.sum() == 0


def test_unverified_geometry_and_wrong_rgb_layout_fail_closed():
    with pytest.raises(ValueError, match="lens"):
        render_rgb_surface_tile(FRAME, np.zeros((11, 11, 3), dtype=np.uint8),
                                replace(GEOMETRY, lens_undistortion_verified=False), PLANE, TILE)
    with pytest.raises(ValueError, match="BGR"):
        render_rgb_surface_tile(FRAME, np.zeros((11, 11), dtype=np.uint8), GEOMETRY, PLANE, TILE)
    with pytest.raises(ValueError, match="limit"):
        render_rgb_surface_tile(FRAME, np.zeros((11, 11, 3), dtype=np.uint8),
                                GEOMETRY, PLANE, RGBSurfaceTile(0, 0, ModuleSurfaceGrid(0, 0, 1, 2049, 1)))
