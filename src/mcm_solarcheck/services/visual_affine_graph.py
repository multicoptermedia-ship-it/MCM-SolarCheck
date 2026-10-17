"""Non-metric global affine graph fit for RGB or thermal-display imagery.

Affine-only model: not projective bundle adjustment, camera pose or orthophoto.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class AffineGraphFit:
    transforms_to_anchor: tuple[np.ndarray, ...]
    rms_matrix_error: float
    preview_only: bool = True
    metric_orthophoto_verified: bool = False


def fit_affine_graph(frame_count, links, *, max_frames=8, max_error=0.1):
    """Fit frame-to-anchor affine matrices from directed i->j affine links.

    For each edge H_ij, minimize ||T_i - T_j H_ij|| in affine parameters,
    anchoring T_0=identity. Matrix error is dimensionless and is NOT pixels.
    """
    if type(frame_count) is not int or not 2 <= frame_count <= max_frames <= 8:
        raise ValueError("invalid frame count")
    if not np.isfinite(max_error) or max_error <= 0:
        raise ValueError("invalid affine error threshold")
    links = tuple(links)
    if not links or len(links) > 28:
        raise ValueError("invalid link count")
    rows, targets = [], []
    neighbors = [set() for _ in range(frame_count)]
    for i, j, h, weight in links:
        if type(i) is not int or type(j) is not int or not 0 <= i < j < frame_count:
            raise ValueError("invalid link indices")
        h = np.asarray(h, dtype=np.float64)
        if h.shape != (3, 3) or not np.isfinite(h).all() or abs(h[2, 2]) < 1e-10:
            raise ValueError("invalid link matrix")
        h = h / h[2, 2]
        if not np.allclose(h[2], [0., 0., 1.], atol=1e-7):
            raise ValueError("perspective link not supported by affine solver")
        if not np.isfinite(weight) or weight <= 0:
            raise ValueError("invalid link weight")
        neighbors[i].add(j)
        neighbors[j].add(i)
        # For each output coordinate: [a_i,b_i,t_i] = [a_j,b_j,t_j] H_ij.
        for coordinate in range(2):
            for column in range(3):
                row = np.zeros((frame_count - 1) * 6)
                known = 0.
                for frame, matrix_column, sign in ((i, column, 1.),):
                    for k in range(3):
                        coefficient = sign * (1. if k == column else 0.)
                        if frame == 0:
                            known += coefficient * (1. if k == coordinate else 0.)
                        else:
                            row[(frame - 1) * 6 + coordinate * 3 + k] += coefficient
                for k in range(3):
                    coefficient = -h[k, column]
                    if j == 0:
                        known += coefficient * (1. if k == coordinate else 0.)
                    else:
                        row[(j - 1) * 6 + coordinate * 3 + k] += coefficient
                rows.append(row * np.sqrt(weight))
                targets.append(-known * np.sqrt(weight))
    seen, pending = {0}, [0]
    while pending:
        for nxt in neighbors[pending.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                pending.append(nxt)
    if len(seen) != frame_count:
        raise ValueError("disconnected affine graph")
    a = np.asarray(rows)
    y = np.asarray(targets)
    solution, _, rank, _ = np.linalg.lstsq(a, y, rcond=None)
    if rank != (frame_count - 1) * 6:
        raise ValueError("underdetermined affine graph")
    matrices = [np.eye(3)]
    for index in range(frame_count - 1):
        t = np.eye(3)
        t[:2, :] = solution[index * 6:(index + 1) * 6].reshape(2, 3)
        if not np.isfinite(t).all() or abs(np.linalg.det(t[:2, :2])) < 1e-8:
            raise ValueError("degenerate affine solution")
        matrices.append(t)
    error = float(np.sqrt(np.mean((a @ solution - y) ** 2)))
    if error > max_error:
        raise ValueError("inconsistent affine graph")
    return AffineGraphFit(tuple(matrices), error)
