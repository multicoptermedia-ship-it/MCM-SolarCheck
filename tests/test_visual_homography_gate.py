"""Synthetic geometric plausibility tests."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_homography_gate import validate_visual_homography


def test_identity_is_plausible():
    assert validate_visual_homography(np.eye(3), 800, 600) == pytest.approx(1.0)


def test_collapsed_projection_is_rejected():
    with pytest.raises(ValueError, match="area"):
        validate_visual_homography(np.diag([.1, .1, 1.]), 800, 600)


def test_large_expansion_is_rejected():
    with pytest.raises(ValueError, match="area"):
        validate_visual_homography(np.diag([3., 3., 1.]), 800, 600)


def test_singular_transform_is_rejected():
    with pytest.raises(ValueError, match="homography"):
        validate_visual_homography(np.zeros((3, 3)), 800, 600)


def test_nonfinite_transform_is_rejected():
    matrix = np.eye(3)
    matrix[0, 0] = np.nan
    with pytest.raises(ValueError, match="homography"):
        validate_visual_homography(matrix, 800, 600)
