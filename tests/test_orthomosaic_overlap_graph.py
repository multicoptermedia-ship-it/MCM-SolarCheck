import pytest

from mcm_solarcheck.services.orthomosaic_input_validation import OverlapState
from mcm_solarcheck.services.orthomosaic_overlap_graph import (
    PairFeatureEvidence, assess_overlap_connectivity,
)
from mcm_solarcheck.services.orthomosaic_overlap_decision import (
    decide_overlap_from_connectivity, confirmed_project_overlap_failure,
)


def pair(a, b, n=30):
    return PairFeatureEvidence(a, b, n + 5, n, "ransac-homography")


def test_connected_chain_is_not_automatically_approved():
    graph = assess_overlap_connectivity(("a", "b", "c"), (pair("a", "b"), pair("b", "c")))
    assert graph.connected and graph.verified_edge_count == 2
    result = decide_overlap_from_connectivity(graph, evidence_reference="audit-1")
    assert result.assessment.state == OverlapState.UNKNOWN
    assert result.needs_worker_review


def test_single_missing_link_is_not_premature_project_failure():
    graph = assess_overlap_connectivity(("a", "b", "c"), (pair("a", "b"),))
    assert not graph.connected
    assert decide_overlap_from_connectivity(graph, evidence_reference="audit-2").assessment.state == OverlapState.UNKNOWN
    with pytest.raises(ValueError):
        confirmed_project_overlap_failure(graph, method="feature_worker", evidence_reference="audit-2",
                                          full_project_assessment_completed=False)


def test_completed_failure_requires_evidence():
    graph = assess_overlap_connectivity(("a", "b", "c"), (pair("a", "b"),))
    verdict = confirmed_project_overlap_failure(graph, method="feature_worker",
        evidence_reference="audit-3", full_project_assessment_completed=True)
    assert verdict.assessment.state == OverlapState.INSUFFICIENT


def test_invalid_counts_and_unknown_frames_rejected():
    with pytest.raises(ValueError):
        pair("a", "a")
    with pytest.raises(ValueError):
        PairFeatureEvidence("a", "b", 3, 4, "matcher")
    with pytest.raises(ValueError):
        assess_overlap_connectivity(("a", "b"), (pair("a", "c"),))
