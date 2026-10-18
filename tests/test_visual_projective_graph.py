"""Synthetic projective graph refinement and fail-closed tests."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_projective_graph import fit_projective_graph


def _h(dx=0., dy=0., perspective=0.):
    return np.array([[1., 0., dx], [0., 1., dy], [perspective, 0., 1.]])


def test_projective_triangle_refines_to_consistent_anchor():
    first = _h(10., 2., .0001)
    second = _h(5., -3., -.00005)
    direct = second @ first
    direct /= direct[2, 2]
    result = fit_projective_graph([(256, 320)] * 3,
                                  [(0, 1, first, 100.), (1, 2, second, 100.),
                                   (0, 2, direct, 100.)])
    assert result.rms_corner_error_px < .01
    assert np.allclose(result.transforms_to_anchor[0], np.eye(3))
    assert result.preview_only and not result.metric_orthophoto_verified


def test_disconnected_projective_graph_fails():
    with pytest.raises(ValueError, match="disconnected"):
        fit_projective_graph([(256, 320)] * 3, [(0, 1, _h(), 1.)])


def test_invalid_homography_fails():
    with pytest.raises(ValueError, match="invalid projective link"):
        fit_projective_graph([(256, 320)] * 2, [(0, 1, np.zeros((3, 3)), 1.)])


def test_inconsistent_triangle_fails_closed():
    with pytest.raises(ValueError):
        fit_projective_graph([(256, 320)] * 3,
                             [(0, 1, _h(10), 100.), (1, 2, _h(10), 100.),
                              (0, 2, _h(100), 100.)], max_rms_px=1.)
