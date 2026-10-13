"""Evaluate explicit neighboring RGB frame pairs without declaring project success."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.services.orthomosaic_overlap_graph import (
    OverlapConnectivity, assess_overlap_connectivity,
)
from mcm_solarcheck.services.orthomosaic_rgb_feature_matcher import (
    RGBFeatureMatchResult, match_rgb_feature_pair,
)


@dataclass(frozen=True)
class RGBOverlapBatch:
    pairs: tuple[RGBFeatureMatchResult, ...]
    connectivity: OverlapConnectivity
    project_overlap_verified: bool = False


def inspect_rgb_neighbor_pairs(
    frames: tuple[tuple[str, str | Path], ...],
    *,
    min_inliers: int = 20,
) -> RGBOverlapBatch:
    if len(frames) < 2 or len({frame_id for frame_id, _ in frames}) != len(frames):
        raise ValueError("at least two distinct RGB frames required")
    results = tuple(
        match_rgb_feature_pair(first_id, first_path, second_id, second_path,
                               minimum_inliers=min_inliers)
        for (first_id, first_path), (second_id, second_path) in zip(frames, frames[1:])
    )
    # A weak inlier fraction must not become a graph edge merely because
    # the raw inlier count exceeds the threshold.
    evidence = tuple(result.evidence for result in results if result.geometrically_plausible)
    graph = assess_overlap_connectivity(tuple(frame_id for frame_id, _ in frames),
                                        evidence, min_inliers=min_inliers)
    return RGBOverlapBatch(results, graph)
