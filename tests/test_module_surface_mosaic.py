"""Synthetic tests for deterministic conservative module-plane mosaicking."""
import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid, RectifiedModuleSurface
from mcm_solarcheck.services.module_surface_mosaic import mosaic_rectified_surfaces

GRID = ModuleSurfaceGrid(0, 0, 0.1, 2, 2)


def surface(value, mask, *, grid=GRID, dtype=np.uint16):
    return RectifiedModuleSurface(np.full((2, 2), value, dtype=dtype), np.array(mask, dtype=bool), grid)


def test_complementary_raw_thermal_frames_fill_shared_surface():
    a = surface(100, [[True, False], [True, False]])
    b = surface(200, [[False, True], [False, True]])
    result = mosaic_rectified_surfaces((a, b))
    np.testing.assert_array_equal(result.image, [[100, 200], [100, 200]])
    assert result.coverage_fraction == 1
    assert result.contributor_count.max() == 1
    assert not result.thermal_calibration_verified
    assert not result.georeferencing_verified


def test_overlap_uses_first_frame_and_tracks_contributors():
    a = surface(100, [[True, True], [False, False]])
    b = surface(200, [[True, False], [True, True]])
    result = mosaic_rectified_surfaces((a, b))
    np.testing.assert_array_equal(result.image, [[100, 100], [200, 200]])
    assert result.contributor_count[0, 0] == 2


def test_partial_coverage_is_explicit_or_rejected():
    a = surface(100, [[True, False], [False, False]])
    with pytest.raises(ValueError, match="coverage"):
        mosaic_rectified_surfaces((a,))
    result = mosaic_rectified_surfaces((a,), require_full_coverage=False)
    assert result.coverage_fraction == 0.25
    assert not result.valid_mask[1, 1]


def test_reject_different_surface_grids_and_pixel_budget():
    a = surface(100, [[True, True], [True, True]])
    b = surface(200, [[True, True], [True, True]], grid=ModuleSurfaceGrid(1, 0, 0.1, 2, 2))
    with pytest.raises(ValueError, match="identical"):
        mosaic_rectified_surfaces((a, b))
    with pytest.raises(ValueError, match="budget"):
        mosaic_rectified_surfaces((a,), max_pixels=3)
