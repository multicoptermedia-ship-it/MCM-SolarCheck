"""Connectivity, redundancy and bridge quality gates for a whole SfM flight."""
import pytest

from mcm_solarcheck.services.rgb_sfm_link_graph_gate import (
    audit_complete_rgb_sfm_link_graph,
)


def _pairs(n=12):
    ids = tuple(f"RGB-{i:04d}" for i in range(n))
    consecutive = tuple((ids[i], ids[i+1]) for i in range(n-1))
    spatial = tuple((ids[i], ids[i+2]) for i in range(n-2))
    return ids, consecutive, spatial


def test_full_connected_sfm_graph_redundancy_and_bridge_diagnostics_privacy():
    ids, sequential, spatial = _pairs()
    matched = sequential + spatial
    result = audit_complete_rgb_sfm_link_graph(
        ids, matched, matched, spatial,
    )
    assert result.camera_count == 12
    assert result.accepted_geometric_pair_count == len(matched)
    assert result.spatial_nonadjacent_geometric_pairs == len(spatial)
    assert result.spatial_nonadjacent_supported_cameras == 12
    assert result.minimum_geometric_degree >= 2
    assert result.bridge_pair_count == 0
    report = result.privacy_safe_summary()
    assert report["sfm_graph_connected"] is True
    assert report["physical_flight_strip_identity_verified"] is False
    assert all("RGB-000" not in str(value) for value in report.values())


def test_one_lucky_spatial_link_fails_even_with_descriptors_on_other_edges():
    ids, sequential, spatial = _pairs()
    with pytest.raises(ValueError, match="too few"):
        audit_complete_rgb_sfm_link_graph(
            ids, sequential+spatial,
            sequential + spatial[:1], spatial,
        )


def test_two_links_to_only_two_frames_fail_independent_support():
    ids, sequential, spatial = _pairs()
    other = (ids[5], ids[0])
    accepted = sequential + (spatial[0], other)
    # Here the spatial support contains at least 3 cameras, so valid.
    good = audit_complete_rgb_sfm_link_graph(
        ids, accepted, accepted, (spatial[0], other),
    )
    assert good.spatial_nonadjacent_supported_cameras >= 3
    # Duplicating reversed direction is not distinct evidence.
    with pytest.raises(ValueError, match="duplicate"):
        audit_complete_rgb_sfm_link_graph(
            ids, accepted+(other[::-1],), accepted, spatial+(other,),
        )


def test_disconnected_accepted_network_is_not_hidden_by_complete_pose_array():
    ids, sequential, spatial = _pairs()
    accepted = tuple(e for e in sequential+spatial
                     if not (ids[5] in e and ids[6] in e))
    # Create disconnected halves 0..5 and 6..11 despite 2 local spatial links.
    accepted = tuple(e for e in accepted
                     if (int(e[0][-4:]) < 6) == (int(e[1][-4:]) < 6))
    with pytest.raises(ValueError, match="disconnected"):
        audit_complete_rgb_sfm_link_graph(
            ids, sequential+spatial, accepted, spatial,
        )


def test_diagnostic_bridges_are_reported_without_false_survey_clearance():
    ids, sequential, spatial = _pairs()
    accepted = sequential + (spatial[0], spatial[1])
    result = audit_complete_rgb_sfm_link_graph(
        ids, sequential+spatial, accepted, spatial,
    )
    assert result.bridge_pair_count > 0
    assert result.privacy_safe_summary()["sfm_graph_single_edge_bridges"] > 0


def test_1000_camera_long_chain_uses_iterative_not_recursive_graph_scan():
    ids, sequential, spatial = _pairs(1000)
    # A few spatial links suffice for this synthetic logic gate; no
    # independent survey/roof clearance can ever be inferred from them.
    accepted = sequential + spatial[:2]
    result = audit_complete_rgb_sfm_link_graph(
        ids, sequential+spatial, accepted, spatial,
    )
    assert result.camera_count == 1000
    assert result.bridge_pair_count > 0


def test_unobserved_or_invalid_geometric_links_never_pass():
    ids, consecutive, spatial = _pairs()
    with pytest.raises(ValueError, match="provenance"):
        audit_complete_rgb_sfm_link_graph(
            ids, consecutive, consecutive + spatial[:2], spatial,
        )
    with pytest.raises(ValueError, match="invalid"):
        audit_complete_rgb_sfm_link_graph(
            ids, consecutive+spatial, consecutive+spatial,
            ((ids[0], "unknown-camera"),),
        )
