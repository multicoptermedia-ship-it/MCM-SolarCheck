"""Non-metric visual graph coverage diagnostics; independent of image modality."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisualGraphCoverage:
    frame_count: int
    verified_pairs: tuple[tuple[int, int], ...]
    missing_pairs: tuple[tuple[int, int], ...]
    bridge_pairs: tuple[tuple[int, int], ...]
    redundant: bool


def audit_visual_graph_coverage(frame_count, verified_pairs):
    """Identify single-link failure points in a small undirected visual graph.

    A connected graph without bridges has alternate visual paths for each link.
    This does not establish pixel accuracy, camera calibration or metric scale.
    """
    if type(frame_count) is not int or not 3 <= frame_count <= 8:
        raise ValueError("invalid frame count")
    pairs = tuple(verified_pairs)
    if len(pairs) > frame_count * (frame_count - 1) // 2:
        raise ValueError("too many links")
    found = set()
    for i, j in pairs:
        if type(i) is not int or type(j) is not int or not 0 <= i < j < frame_count:
            raise ValueError("invalid pair indices")
        if (i, j) in found:
            raise ValueError("duplicate pair")
        found.add((i, j))
    all_pairs = {(i, j) for i in range(frame_count) for j in range(i + 1, frame_count)}

    def connected(without=None):
        visited = {0}
        pending = [0]
        while pending:
            current = pending.pop()
            for i, j in found:
                if (i, j) == without:
                    continue
                neighbor = j if i == current else i if j == current else None
                if neighbor is not None and neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        return len(visited) == frame_count

    bridges = tuple(sorted(edge for edge in found if not connected(edge)))
    return VisualGraphCoverage(frame_count, tuple(sorted(found)),
                               tuple(sorted(all_pairs - found)), bridges,
                               connected() and not bridges)


def require_redundant_visual_graph(frame_count, verified_pairs):
    coverage = audit_visual_graph_coverage(frame_count, verified_pairs)
    if not coverage.redundant:
        raise ValueError("visual graph lacks redundant overlap paths")
    return coverage
