"""Fail-closed plausibility gate for non-metric pairwise homographies."""
from __future__ import annotations

import cv2
import numpy as np


def validate_visual_homography(matrix, source_width, source_height, *, min_area_ratio=0.35, max_area_ratio=3.0, max_edge_ratio=4.0):
    """Reject folded, collapsed, wildly stretched or nonfinite preview transforms.

    This is a heuristic image-to-image check, NOT camera calibration or orthorectification.
    """
    h = np.asarray(matrix, dtype=np.float64)
    if h.shape != (3, 3) or not np.isfinite(h).all() or abs(np.linalg.det(h)) < 1e-12:
        raise ValueError("invalid homography")
    if not (source_width > 0 and source_height > 0):
        raise ValueError("invalid source dimensions")
    if not (0 < min_area_ratio < 1 < max_area_ratio and max_edge_ratio >= 1):
        raise ValueError("invalid homography thresholds")
    corners = np.float32([[0, 0], [source_width, 0], [source_width, source_height], [0, source_height]]).reshape(-1, 1, 2)
    transformed = cv2.perspectiveTransform(corners, h).reshape(4, 2)
    if not np.isfinite(transformed).all():
        raise ValueError("nonfinite projected corners")
    area = float(cv2.contourArea(transformed))
    ratio = area / (source_width * source_height)
    if not min_area_ratio <= ratio <= max_area_ratio:
        raise ValueError("implausible projected area")
    edges = np.linalg.norm(np.roll(transformed, -1, axis=0) - transformed, axis=1)
    if np.min(edges) <= 1e-6 or np.max(edges) / np.min(edges) > max_edge_ratio * max(source_width, source_height) / min(source_width, source_height):
        raise ValueError("implausible projected edge lengths")
    cross = np.cross(np.roll(transformed, -1, axis=0) - transformed, np.roll(transformed, -2, axis=0) - np.roll(transformed, -1, axis=0))
    if not (np.all(cross > 1e-5) or np.all(cross < -1e-5)):
        raise ValueError("folded or nonconvex projected image")
    return ratio
