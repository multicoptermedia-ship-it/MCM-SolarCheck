"""Run actual RGB pixel matching across selected flight-wide candidate edges."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.services.orthomosaic_overlap_candidates import (
    CandidatePair, select_overlap_candidates,
)
from mcm_solarcheck.services.orthomosaic_overlap_graph import (
    OverlapConnectivity, assess_overlap_connectivity,
)
from mcm_solarcheck.services.orthomosaic_rgb_feature_matcher import (
    RGBFeatureMatchResult, match_rgb_feature_pair,
)


@dataclass(frozen=True)
class ProjectRGBOverlapAudit:
    candidates: tuple[CandidatePair, ...]
    results: tuple[RGBFeatureMatchResult, ...]
    connectivity: OverlapConnectivity
    project_overlap_verified: bool = False

    def to_summary(self) -> dict[str, object]:
        return {
            "frame_count": self.connectivity.image_count,
            "candidate_count": len(self.candidates),
            "verified_edge_count": self.connectivity.verified_edge_count,
            "feature_graph_connected": self.connectivity.connected,
            "project_overlap_verified": False,
            "pairs": [
                {"first_id": candidate.first_id, "second_id": candidate.second_id,
                 "reason": candidate.reason, "tentative_matches": result.evidence.tentative_matches,
                 "verified_inliers": result.evidence.verified_inliers,
                 "verifier": result.evidence.verifier,
                 "geometrically_plausible": result.geometrically_plausible}
                for candidate, result in zip(self.candidates, self.results)
            ],
        }


def inspect_rgb_project_overlap(
    frames: tuple[tuple[str, str | Path], ...],
    *,
    cross_strip_pairs: tuple[tuple[str, str], ...] = (),
    min_inliers: int = 20,
    max_candidates: int = 10000,
) -> ProjectRGBOverlapAudit:
    ids = tuple(frame_id for frame_id, _ in frames)
    candidates = select_overlap_candidates(ids, cross_strip_pairs=cross_strip_pairs,
                                           max_candidates=max_candidates)
    paths = dict(frames)
    results = tuple(
        match_rgb_feature_pair(candidate.first_id, paths[candidate.first_id],
                               candidate.second_id, paths[candidate.second_id],
                               minimum_inliers=min_inliers)
        for candidate in candidates
    )
    evidence = tuple(result.evidence for result in results if result.geometrically_plausible)
    graph = assess_overlap_connectivity(ids, evidence, min_inliers=min_inliers)
    return ProjectRGBOverlapAudit(candidates, results, graph)
