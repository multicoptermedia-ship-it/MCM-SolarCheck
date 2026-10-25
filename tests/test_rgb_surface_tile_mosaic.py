"""Multi-frame RGB tile mosaics are explicitly unverified and retain gaps."""
from pathlib import Path
import numpy as np
import pytest

from mcm_solarcheck.domain.models import ImageFrame, Pose
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D,
)
from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid
from mcm_solarcheck.services.rgb_surface_tile_mosaic import (
    RGBMosaicSource, compose_rgb_roof_tile,
)
from mcm_solarcheck.services.rgb_surface_tiles import RGBSurfaceTile

PLANE = SurveyedPlane3D((0, 0, 0), (0, 0, 1))
CAMERA = VerifiedCameraGeometry(
    PinholeIntrinsics(10, 10, 5, 5),
    CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.))),
    11, 11, "synthetic calibration", "synthetic ENU", "synthetic survey", True, True,
)
TILE = RGBSurfaceTile(0, 0, ModuleSurfaceGrid(-.5, -.5, 1., 1, 1))


def source(identifier, value):
    frame = ImageFrame(identifier, Path("synthetic.jpg"), width=11, height=11,
                       camera_pose=Pose(yaw_deg=0, pitch_deg=-90, roll_deg=0))
    pixels = np.full((11, 11, 3), value, dtype=np.uint8)
    return RGBMosaicSource(frame, pixels, CAMERA)


def test_identical_views_reuse_geometry_and_count_overlap():
    a, b = source("a", 100), source("b", 100)
    mosaic = compose_rgb_roof_tile((a, b), PLANE, TILE)
    assert mosaic.total_sources == 2
    assert mosaic.contributing_sources == 2
    assert mosaic.overlapping_observations == 1
    assert mosaic.mean_absolute_overlap_difference == pytest.approx(0)
    assert mosaic.bgr[0, 0, 0] == 100
    assert mosaic.valid_mask.all()
    assert not mosaic.orthophoto_verified
    assert mosaic.status == "unverified_multi_view_plane_preview"
    assert np.all(a.undistorted_bgr == 100)


def test_conflicting_pixels_are_audited_not_silently_averaged():
    mosaic = compose_rgb_roof_tile((source("a", 100), source("b", 200)), PLANE, TILE)
    assert mosaic.bgr[0, 0, 0] == 100
    assert mosaic.mean_absolute_overlap_difference == pytest.approx(100.)


def test_outside_tile_remains_missing_without_fabricating_completeness():
    far = RGBSurfaceTile(0, 0, ModuleSurfaceGrid(1000, 1000, 1., 2, 2))
    mosaic = compose_rgb_roof_tile((source("a", 100), source("b", 100)), PLANE, far)
    assert mosaic.contributing_sources == 0
    assert mosaic.overlapping_observations == 0
    assert not mosaic.valid_mask.any()
    assert mosaic.bgr.sum() == 0
    assert mosaic.mean_absolute_overlap_difference is None


def test_duplicate_sources_and_unbounded_counts_rejected():
    with pytest.raises(ValueError, match="unique"):
        compose_rgb_roof_tile((source("a", 1), source("a", 2)), PLANE, TILE)
    with pytest.raises(ValueError, match="bounded"):
        compose_rgb_roof_tile((source("a", 1), source("b", 2)), PLANE, TILE, max_sources=1)
