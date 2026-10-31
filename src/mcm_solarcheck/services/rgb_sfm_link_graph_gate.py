"""Provenance and redundancy audit for the COMPLETE calibrated RGB SfM link graph.

Only links accepted by the existing essential-RANSAC/relative-pose solver can
count here. GNSS nonadjacency suggests spatial overlap, NOT physical strips.
All identifiers stay private; summaries contain counts alone. No dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RGBSfMLinkGraphAudit:
    camera_count: int
    accepted_geometric_pair_count: int
    spatial_nonadjacent_geometric_pairs: int
    spatial_nonadjacent_supported_cameras: int
    minimum_geometric_degree: int
    bridge_pair_count: int
    status: str = "connected_sfm_link_graph_not_3d_or_survey_verified"

    def privacy_safe_summary(self) -> dict:
        return {
            "sfm_geometrically_accepted_pairs": self.accepted_geometric_pair_count,
            "sfm_geometric_nonadjacent_pairs": self.spatial_nonadjacent_geometric_pairs,
            "sfm_geometric_nonadjacent_supported_cameras": (
                self.spatial_nonadjacent_supported_cameras
            ),
            "sfm_graph_min_camera_degree": self.minimum_geometric_degree,
            "sfm_graph_single_edge_bridges": self.bridge_pair_count,
            "sfm_graph_connected": True,
            "physical_flight_strip_identity_verified": False,
        }


def audit_complete_rgb_sfm_link_graph(
    frame_ids: tuple[str, ...],
    matched_pairs: tuple[tuple[str, str], ...],
    calibrated_accepted_pairs: tuple[tuple[str, str], ...],
    proposed_spatial_nonadjacent_pairs: tuple[tuple[str, str], ...],
) -> RGBSfMLinkGraphAudit:
    """Reject missing cameras, disconnected networks and single lucky spatial link.

    The accepted graph must be connected over *all* frames, with at least two
    accepted spatial-nonadjacent links supported by at least three distinct
    frames. Bridge count is diagnostic, NOT independently verified geometry.
    """
    if (type(frame_ids) is not tuple or not 12 <= len(frame_ids) <= 1000
            or any(not isinstance(fid, str) or not fid for fid in frame_ids)
            or len(frame_ids) != len(set(frame_ids))):
        raise ValueError("complete unique SfM camera frame list required")
    names = set(frame_ids)

    def pairs(values, title):
        if type(values) is not tuple:
            raise ValueError(f"invalid {title} paired-camera evidence")
        seen = set()
        for pair in values:
            if (type(pair) is not tuple or len(pair) != 2
                    or pair[0] not in names or pair[1] not in names
                    or pair[0] == pair[1]):
                raise ValueError(f"invalid {title} paired-camera evidence")
            edge = frozenset(pair)
            if edge in seen:
                raise ValueError(f"duplicate {title} paired-camera evidence")
            seen.add(edge)
        return seen

    matched = pairs(matched_pairs, "descriptor-matched")
    accepted = pairs(calibrated_accepted_pairs, "geometrically accepted")
    spatial = pairs(proposed_spatial_nonadjacent_pairs, "GNSS-suggested")
    if not accepted or not accepted.issubset(matched):
        raise ValueError("SfM geometric pair lacks observed descriptor provenance")
    nonadjacent = accepted & spatial
    supporting = set().union(*nonadjacent) if nonadjacent else set()
    if len(nonadjacent) < 2 or len(supporting) < 3:
        raise ValueError("too few independently placed SfM geometric spatial links")

    id_to_index = {x: i for i, x in enumerate(frame_ids)}
    edges = [tuple(id_to_index[fid] for fid in edge) for edge in accepted]
    graph = [[] for _ in frame_ids]
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)
    degree = min(len(node) for node in graph)
    if degree == 0:
        raise ValueError("SfM geometric graph has unlinked RGB cameras")

    # Tarjan bridge audit also establishes whole-graph connectivity.
    discovery = [-1] * len(frame_ids)
    low = [0] * len(frame_ids)
    tick = 0
    bridges = 0

    # Explicit enter/exit stack avoids Python recursion limits at 1000 frames.
    def scan_iterative(start: int):
        nonlocal tick, bridges
        parent = [-1] * len(frame_ids)
        stack = [(start, 0)]
        discovery[start] = low[start] = tick
        tick += 1
        while stack:
            vertex, offset = stack[-1]
            if offset == len(graph[vertex]):
                stack.pop()
                p = parent[vertex]
                if p != -1:
                    low[p] = min(low[p], low[vertex])
                    if low[vertex] > discovery[p]:
                        bridges += 1
                continue
            target = graph[vertex][offset]
            stack[-1] = (vertex, offset + 1)
            if target == parent[vertex]:
                continue
            if discovery[target] == -1:
                parent[target] = vertex
                discovery[target] = low[target] = tick
                tick += 1
                stack.append((target, 0))
            else:
                low[vertex] = min(low[vertex], discovery[target])

    scan_iterative(0)
    if any(x == -1 for x in discovery):
        raise ValueError("disconnected calibrated RGB SfM geometric link graph")
    return RGBSfMLinkGraphAudit(
        len(frame_ids), len(accepted), len(nonadjacent), len(supporting),
        degree, bridges,
    )
