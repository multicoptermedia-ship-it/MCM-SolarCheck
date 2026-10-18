"""Visual overlap graph redundancy gate synthetic tests."""
import pytest

from mcm_solarcheck.services.visual_graph_coverage import (
    audit_visual_graph_coverage, require_redundant_visual_graph,
)


def test_triangle_has_independent_overlap_paths():
    result = require_redundant_visual_graph(3, [(0, 1), (0, 2), (1, 2)])
    assert result.redundant
    assert result.bridge_pairs == ()
    assert result.missing_pairs == ()


def test_connected_chain_has_unverifiable_single_link_bridges():
    result = audit_visual_graph_coverage(4, [(0, 1), (1, 2), (2, 3)])
    assert not result.redundant
    assert result.bridge_pairs == ((0, 1), (1, 2), (2, 3))
    with pytest.raises(ValueError, match="redundant"):
        require_redundant_visual_graph(4, result.verified_pairs)


def test_disconnected_graph_not_redundant():
    result = audit_visual_graph_coverage(4, [(0, 1), (2, 3)])
    assert not result.redundant


def test_duplicate_and_reversed_pairs_fail_closed():
    with pytest.raises(ValueError, match="duplicate"):
        audit_visual_graph_coverage(3, [(0, 1), (0, 1)])
    with pytest.raises(ValueError, match="indices"):
        audit_visual_graph_coverage(3, [(1, 0)])
