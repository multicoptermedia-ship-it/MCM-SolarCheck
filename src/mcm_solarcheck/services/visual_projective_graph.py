"""Bounded projective multi-view graph refinement in preview pixels, not metric BA."""
from __future__ import annotations

from dataclasses import dataclass
import cv2
import numpy as np


@dataclass(frozen=True)
class ProjectiveGraphFit:
    transforms_to_anchor: tuple[np.ndarray, ...]
    rms_corner_error_px: float
    preview_only: bool = True
    metric_orthophoto_verified: bool = False


def fit_projective_graph(frame_shapes, links, *, max_frames=8, max_rms_px=12., iterations=12):
    """Refine image-to-anchor homographies using overlapping pair corner constraints.

    Links: (i,j,H_i_to_j,weight). Anchor T0=I. Numerical Gauss-Newton,
    damping and strict bounded dimensions. This is NOT feature-track bundle adjustment.
    """
    shapes = tuple(frame_shapes)
    n = len(shapes)
    if not 2 <= n <= max_frames <= 8 or not 1 <= iterations <= 30:
        raise ValueError("invalid graph size or iteration limit")
    if not np.isfinite(max_rms_px) or max_rms_px <= 0:
        raise ValueError("invalid corner error threshold")
    edges = []
    adjacency = [[] for _ in shapes]
    for i, j, h, weight in tuple(links):
        if type(i) is not int or type(j) is not int or not 0 <= i < j < n:
            raise ValueError("invalid link indices")
        h = np.asarray(h, dtype=np.float64)
        if h.shape != (3, 3) or not np.isfinite(h).all() or abs(h[2, 2]) < 1e-10:
            raise ValueError("invalid projective link")
        h = h / h[2, 2]
        if abs(np.linalg.det(h)) < 1e-10 or not np.isfinite(weight) or weight <= 0:
            raise ValueError("degenerate projective link")
        edges.append((i, j, h, min(float(weight), 500.)))
        adjacency[i].append((j, h))
        adjacency[j].append((i, np.linalg.inv(h)))
    if not edges or len(edges) > 28:
        raise ValueError("invalid link count")
    for height, width in shapes:
        if not 128 <= height <= 10000 or not 128 <= width <= 10000:
            raise ValueError("invalid image dimensions")
    # BFS initializes each frame->anchor transform from independently estimated links.
    transforms = [None] * n
    transforms[0] = np.eye(3)
    queue = [0]
    while queue:
        i = queue.pop(0)
        for j, h_i_to_j in adjacency[i]:
            if transforms[j] is None:
                transforms[j] = transforms[i] @ np.linalg.inv(h_i_to_j)
                transforms[j] /= transforms[j][2, 2]
                queue.append(j)
    if any(t is None for t in transforms):
        raise ValueError("disconnected projective graph")
    corners = []
    for height, width in shapes:
        corners.append(np.float64([[0, 0], [width, 0], [width, height], [0, height]]).reshape(-1, 1, 2))
    def encode(t):
        return np.concatenate([x.flatten()[:8] for x in t[1:]])
    def decode(p):
        out = [np.eye(3)]
        for k in range(n - 1):
            h = np.append(p[k * 8:(k + 1) * 8], 1.).reshape(3, 3)
            out.append(h)
        return out
    def residual(p):
        ts = decode(p)
        pieces = []
        for i, j, h, weight in edges:
            try:
                source = cv2.perspectiveTransform(corners[i], ts[i]).reshape(-1, 2)
                mapped = cv2.perspectiveTransform(corners[i], ts[j] @ h).reshape(-1, 2)
            except cv2.error:
                return None
            delta = (source - mapped) * np.sqrt(weight / 100.)
            if not np.isfinite(delta).all() or np.max(np.abs(delta)) > 1e7:
                return None
            pieces.extend(delta.flatten())
        return np.asarray(pieces)
    p = encode(transforms)
    for _ in range(iterations):
        base = residual(p)
        if base is None:
            raise ValueError("invalid projective projection")
        jac = np.empty((len(base), len(p)))
        for k in range(len(p)):
            step = 1e-6 * max(1., abs(p[k]))
            changed = p.copy()
            changed[k] += step
            other = residual(changed)
            if other is None:
                raise ValueError("invalid projective derivative")
            jac[:, k] = (other - base) / step
        damping = 1e-3
        delta = np.linalg.lstsq(np.vstack([jac, np.eye(len(p)) * damping]),
                                np.concatenate([-base, np.zeros(len(p))]), rcond=None)[0]
        if not np.isfinite(delta).all():
            raise ValueError("invalid projective update")
        improved = False
        for factor in (1., .5, .25, .125):
            candidate = p + factor * delta
            r = residual(candidate)
            if r is not None and np.dot(r, r) < np.dot(base, base):
                p = candidate
                improved = True
                break
        if not improved:
            break
    ts = decode(p)
    for t in ts:
        if not np.isfinite(t).all() or abs(np.linalg.det(t)) < 1e-10:
            raise ValueError("degenerate projective solution")
    # Report unweighted pixel error, not the weighted optimization objective.
    differences = []
    for i, j, h, _ in edges:
        a = cv2.perspectiveTransform(corners[i], ts[i]).reshape(-1, 2)
        b = cv2.perspectiveTransform(corners[i], ts[j] @ h).reshape(-1, 2)
        differences.extend(np.sum((a - b) ** 2, axis=1))
    rms = float(np.sqrt(np.mean(differences)))
    if not np.isfinite(rms) or rms > max_rms_px:
        raise ValueError("inconsistent projective graph")
    return ProjectiveGraphFit(tuple(ts), rms)
