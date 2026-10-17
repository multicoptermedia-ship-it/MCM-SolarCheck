"""Non-metric spatial distribution of verified image correspondences."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class InlierDistribution:
    occupied_cells: int
    total_cells: int
    fraction: float
    spatially_distributed: bool


def assess_inlier_distribution(points_xy, image_width, image_height, *, grid_size=4, min_cells=4):
    """Count grid cells containing RANSAC inliers; NOT a roof coverage percentage."""
    if any(type(v) is not int or v <= 0 for v in (image_width, image_height, grid_size, min_cells)):
        raise ValueError("positive integer image dimensions and grid parameters required")
    if min_cells > grid_size * grid_size:
        raise ValueError("min_cells exceeds grid capacity")
    points = np.asarray(points_xy, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
        raise ValueError("finite Nx2 inlier coordinates required")
    if len(points) and (np.any(points < 0) or np.any(points[:, 0] >= image_width) or np.any(points[:, 1] >= image_height)):
        raise ValueError("inlier coordinates outside image")
    cells = set()
    for x, y in points:
        col = min(grid_size - 1, int(x * grid_size / image_width))
        row = min(grid_size - 1, int(y * grid_size / image_height))
        cells.add((row, col))
    total = grid_size * grid_size
    return InlierDistribution(len(cells), total, len(cells) / total, len(cells) >= min_cells)
