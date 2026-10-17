"""Synthetic regression checks for modality-independent translation graph fitting."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_translation_graph import solve_translation_graph


def test_consistent_triangle_recovers_global_offsets():
    result = solve_translation_graph(3, [(0, 1, 10., 2., 1.), (1, 2, 5., -3., 1.), (0, 2, 15., -1., 1.)])
    assert np.allclose(result.positions_xy, [[0, 0], [10, 2], [15, -1]])
    assert result.rms_residual_px < 1e-8
    assert result.preview_only and not result.metric_orthophoto_verified


def test_inconsistent_loop_rejected():
    with pytest.raises(ValueError, match="inconsistent"):
        solve_translation_graph(3, [(0, 1, 10., 0., 1.), (1, 2, 10., 0., 1.), (0, 2, 90., 0., 1.)])


def test_disconnected_graph_rejected():
    with pytest.raises(ValueError, match="disconnected"):
        solve_translation_graph(4, [(0, 1, 1., 0., 1.), (2, 3, 1., 0., 1.)])


def test_invalid_edge_weight_rejected():
    with pytest.raises(ValueError, match="values"):
        solve_translation_graph(2, [(0, 1, 1., 0., 0.)])


def test_weighted_graph_stays_finite():
    result = solve_translation_graph(3, [(0, 1, 10., 0., 100.), (1, 2, 10., 0., 100.), (0, 2, 21., 0., 1.)])
    assert np.isfinite(result.positions_xy).all()
    assert result.rms_residual_px < 2.
