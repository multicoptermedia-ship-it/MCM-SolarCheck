"""Global affine graph regression tests; non-metric visual geometry."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_affine_graph import fit_affine_graph


def _translation(x, y):
    return np.array([[1., 0., x], [0., 1., y], [0., 0., 1.]])


def test_triangle_recovers_all_anchor_transforms():
    links = [(0, 1, _translation(10, 2), 1.), (1, 2, _translation(5, -3), 1.),
             (0, 2, _translation(15, -1), 1.)]
    fit = fit_affine_graph(3, links)
    assert np.allclose(fit.transforms_to_anchor[1], _translation(-10, -2), atol=1e-6)
    assert np.allclose(fit.transforms_to_anchor[2], _translation(-15, 1), atol=1e-6)
    assert fit.rms_matrix_error < 1e-7
    assert fit.preview_only and not fit.metric_orthophoto_verified


def test_projective_edge_is_rejected():
    h = _translation(10, 0)
    h[2, 0] = .001
    with pytest.raises(ValueError, match="perspective"):
        fit_affine_graph(2, [(0, 1, h, 1.)])


def test_disconnected_graph_is_rejected():
    with pytest.raises(ValueError, match="disconnected"):
        fit_affine_graph(3, [(0, 1, np.eye(3), 1.)])


def test_conflicting_triangle_is_rejected():
    with pytest.raises(ValueError, match="inconsistent"):
        fit_affine_graph(3, [(0, 1, _translation(1, 0), 1.),
                             (1, 2, _translation(1, 0), 1.),
                             (0, 2, _translation(100, 0), 1.)], max_error=.01)
