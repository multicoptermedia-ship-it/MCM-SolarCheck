"""Conservative connectivity checks from externally verified image-feature matches."""
from __future__ import annotations

from dataclasses import dataclass
from collections import deque


@dataclass(frozen=True)
class PairFeatureEvidence:
    first_id: str
    second_id: str
    tentative_matches: int
    verified_inliers: int
    verifier: str

    def __post_init__(self) -> None:
        if not self.first_id or not self.second_id or self.first_id == self.second_id:
            raise ValueError("two distinct image ids required")
        if not self.verifier.strip():
            raise ValueError("feature verifier provenance required")
        if self.tentative_matches < 0 or not 0 <= self.verified_inliers <= self.tentative_matches:
            raise ValueError("invalid feature match counts")


@dataclass(frozen=True)
class OverlapConnectivity:
    image_count: int
    verified_edge_count: int
    connected: bool
    min_inliers: int
    method: str = "verified_feature_match_graph"


def assess_overlap_connectivity(
    image_ids: tuple[str, ...],
    evidence: tuple[PairFeatureEvidence, ...],
    *,
    min_inliers: int = 20,
) -> OverlapConnectivity:
    if len(image_ids) < 2 or len(set(image_ids)) != len(image_ids):
        raise ValueError("at least two distinct images required")
    if min_inliers < 4:
        raise ValueError("minimum inlier threshold must be at least four")
    neighbors = {image_id: set() for image_id in image_ids}
    edges = set()
    for item in evidence:
        if item.first_id not in neighbors or item.second_id not in neighbors:
            raise ValueError("feature evidence references unknown image")
        edge = frozenset((item.first_id, item.second_id))
        if item.verified_inliers >= min_inliers:
            edges.add(edge)
            neighbors[item.first_id].add(item.second_id)
            neighbors[item.second_id].add(item.first_id)
    visited = {image_ids[0]}
    pending = deque([image_ids[0]])
    while pending:
        for other in neighbors[pending.popleft()]:
            if other not in visited:
                visited.add(other)
                pending.append(other)
    return OverlapConnectivity(len(image_ids), len(edges),
                               len(visited) == len(image_ids), min_inliers)
