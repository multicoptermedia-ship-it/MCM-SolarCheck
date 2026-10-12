"""Convert measured overlap connectivity to a conservative preflight state."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.orthomosaic_input_validation import (
    OverlapAssessment, OverlapState,
)
from mcm_solarcheck.services.orthomosaic_overlap_graph import OverlapConnectivity


@dataclass(frozen=True)
class ProjectOverlapVerdict:
    assessment: OverlapAssessment
    connectivity: OverlapConnectivity
    needs_worker_review: bool


def decide_overlap_from_connectivity(
    connectivity: OverlapConnectivity,
    *,
    evidence_reference: str,
) -> ProjectOverlapVerdict:
    if not evidence_reference.strip():
        raise ValueError("audit evidence reference required")
    # Connectivity is necessary but not sufficient: reconstruction/coverage
    # verification must independently confirm overlap before the worker proceeds.
    return ProjectOverlapVerdict(
        assessment=OverlapAssessment(OverlapState.UNKNOWN),
        connectivity=connectivity,
        needs_worker_review=True,
    )


def confirmed_project_overlap_failure(
    connectivity: OverlapConnectivity,
    *,
    method: str,
    evidence_reference: str,
    full_project_assessment_completed: bool,
) -> ProjectOverlapVerdict:
    if not full_project_assessment_completed or connectivity.connected:
        raise ValueError("cannot claim project failure from incomplete or connected evidence")
    return ProjectOverlapVerdict(
        assessment=OverlapAssessment(OverlapState.INSUFFICIENT, method, evidence_reference),
        connectivity=connectivity,
        needs_worker_review=False,
    )
