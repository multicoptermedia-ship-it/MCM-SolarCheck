"""Cancellable in-memory RGB plane-workflow tests with synthetic BGR arrays."""
from pathlib import Path

import numpy as np
import pytest

from mcm_solarcheck.domain.models import ImageFrame, Pose
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D,
)
from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid
from mcm_solarcheck.services.rgb_surface_tiles import plan_rgb_surface_tiles
from mcm_solarcheck.services.rgb_surface_tile_mosaic import RGBMosaicSource
from mcm_solarcheck.services.rgb_surface_pilot_run import (
    RGBSurfacePilotCancelled, run_read_only_rgb_surface_pilot,
)

FRAME = ImageFrame("synthetic", Path("private-not-read.jpg"), width=11, height=11,
                   camera_pose=Pose(yaw_deg=0, pitch_deg=-90, roll_deg=0))
GEOMETRY = VerifiedCameraGeometry(
    PinholeIntrinsics(10, 10, 5, 5),
    CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.))),
    11, 11, "synthetic calibration", "synthetic geometry", "synthetic roof", True, True,
)
PLANE = SurveyedPlane3D((0, 0, 0), (0, 0, 1))


def inputs():
    original = np.full((11, 11, 3), 77, dtype=np.uint8)
    src = RGBMosaicSource(FRAME, original, GEOMETRY)
    plan = plan_rgb_surface_tiles(
        ModuleSurfaceGrid(-.5, -.5, 1., 20, 1), tile_side_px=16,
    )
    return plan, (src,), original


def test_pilot_reports_partial_coverage_and_stable_progress_without_writes(tmp_path):
    plan, sources, original = inputs()
    ticks = []
    before = original.copy()
    result = run_read_only_rgb_surface_pilot(
        plan, sources, PLANE, on_progress=lambda done, total, covered:
        ticks.append((done, total, covered)),
    )
    assert result.processed_tile_count == 2
    assert len(result.tiles) == 2
    assert len(ticks) == 2
    assert ticks[-1][0:2] == (2, 2)
    assert ticks[-1][2] == result.audit.covered_pixels
    assert result.audit.missing_pixels > 0
    assert result.state == "partial_or_missing_coverage_unverified"
    assert result.read_only
    assert not result.orthophoto_verified
    np.testing.assert_array_equal(original, before)
    assert list(tmp_path.iterdir()) == []


def test_cancellation_before_start_and_between_tiles_never_publishes():
    plan, sources, _ = inputs()
    with pytest.raises(RGBSurfacePilotCancelled):
        run_read_only_rgb_surface_pilot(plan, sources, PLANE,
                                        should_cancel=lambda: True)
    flag = {"cancel": False}
    with pytest.raises(RGBSurfacePilotCancelled):
        run_read_only_rgb_surface_pilot(
            plan, sources, PLANE,
            should_cancel=lambda: flag["cancel"],
            on_progress=lambda *args: flag.update(cancel=True),
        )


def test_resource_excess_and_unverified_image_fail_closed():
    plan, sources, original = inputs()
    with pytest.raises(ValueError, match="budget"):
        run_read_only_rgb_surface_pilot(
            plan, sources, PLANE, max_output_pixels=1,
        )
    with pytest.raises(ValueError, match="budget"):
        run_read_only_rgb_surface_pilot(plan, sources, PLANE, max_tiles=1)
    bad = (RGBMosaicSource(FRAME, np.ones((11, 11), dtype=np.uint8), GEOMETRY),)
    with pytest.raises(ValueError, match="BGR"):
        run_read_only_rgb_surface_pilot(plan, bad, PLANE)
