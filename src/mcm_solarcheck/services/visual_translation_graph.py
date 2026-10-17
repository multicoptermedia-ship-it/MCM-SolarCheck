"""Modality-independent, non-metric translation graph least-squares diagnostic.

A translation-only graph is NOT a global homography bundle adjustment.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class TranslationGraphResult:
    positions_xy: np.ndarray
    edge_residuals_px: np.ndarray
    rms_residual_px: float
    preview_only: bool = True
    metric_orthophoto_verified: bool = False


def solve_translation_graph(frame_count, edges, *, max_frames=32, max_rms_px=12.0):
    """Find globally consistent 2-D offsets from (source, target, dx, dy, weight).

    Edge convention: position[target] - position[source] = (dx, dy).
    Fix frame zero at the origin; reject disconnected and inconsistent graphs.
    """
    if type(frame_count) is not int or not 2 <= frame_count <= max_frames <= 32:
        raise ValueError("invalid graph frame count")
    if not np.isfinite(max_rms_px) or max_rms_px <= 0:
        raise ValueError("invalid residual limit")
    edges = tuple(edges)
    if not 1 <= len(edges) <= 256:
        raise ValueError("invalid graph edge count")
    rows, values, weights = [], [], []
    adjacency = [set() for _ in range(frame_count)]
    for edge in edges:
        if len(edge) != 5:
            raise ValueError("edge requires source target dx dy weight")
        source, target, dx, dy, weight = edge
        if (type(source) is not int or type(target) is not int or
                not 0 <= source < frame_count or not 0 <= target < frame_count or source == target):
            raise ValueError("invalid graph edge indices")
        if not np.isfinite([dx, dy, weight]).all() or weight <= 0:
            raise ValueError("invalid graph edge values")
        row = np.zeros(frame_count - 1, dtype=np.float64)
        if source:
            row[source - 1] -= 1.
        if target:
            row[target - 1] += 1.
        rows.append(row)
        values.append((dx, dy))
        weights.append(float(weight))
        adjacency[source].add(target)
        adjacency[target].add(source)
    seen = {0}
    pending = [0]
    while pending:
        for neighbor in adjacency[pending.pop()]:
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    if len(seen) != frame_count:
        raise ValueError("disconnected registration graph")
    a = np.asarray(rows)
    y = np.asarray(values, dtype=np.float64)
    root_w = np.sqrt(np.asarray(weights))[:, None]
    solved, _, rank, _ = np.linalg.lstsq(a * root_w, y * root_w, rcond=None)
    if rank != frame_count - 1:
        raise ValueError("underdetermined registration graph")
    positions = np.vstack((np.zeros((1, 2)), solved))
    residuals = np.linalg.norm(a @ solved - y, axis=1)
    rms = float(np.sqrt(np.mean(residuals ** 2)))
    if rms > max_rms_px:
        raise ValueError("inconsistent registration graph")
    return TranslationGraphResult(positions, residuals, rms)
