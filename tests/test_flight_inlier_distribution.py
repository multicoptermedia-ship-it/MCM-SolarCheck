"""Synthetic grid-distribution checks for image-match evidence."""
import numpy as np
import pytest

from mcm_solarcheck.services.flight_inlier_distribution import assess_inlier_distribution


def test_spread_matches_reach_multiple_grid_cells():
    points = np.array([[10, 10], [35, 10], [65, 10], [90, 10], [10, 40], [90, 90]], dtype=float)
    result = assess_inlier_distribution(points, 100, 100)
    assert result.occupied_cells == 6
    assert result.total_cells == 16
    assert result.spatially_distributed


def test_clustered_matches_do_not_count_as_spread():
    result = assess_inlier_distribution(np.array([[2, 2], [3, 4], [4, 3]], dtype=float), 100, 100)
    assert result.occupied_cells == 1
    assert not result.spatially_distributed


def test_empty_and_out_of_bounds_points():
    result = assess_inlier_distribution(np.empty((0, 2)), 100, 100)
    assert result.occupied_cells == 0
    with pytest.raises(ValueError, match="outside"):
        assess_inlier_distribution(np.array([[100, 1]]), 100, 100)
    with pytest.raises(ValueError, match="finite"):
        assess_inlier_distribution(np.array([[np.nan, 1]]), 100, 100)
