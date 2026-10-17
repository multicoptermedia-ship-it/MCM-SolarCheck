"""Non-metric loop-closure diagnostics for chained visual homographies."""
from __future__ import annotations

import cv2
import numpy as np


def visual_loop_error(chained, direct, width, height):
    """Maximum disagreement in pixels at image corners, not a metric error."""
    a = np.asarray(chained, dtype=np.float64)
    b = np.asarray(direct, dtype=np.float64)
    if a.shape != (3, 3) or b.shape != (3, 3) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("invalid loop homographies")
    if type(width) is not int or type(height) is not int or min(width, height) < 1:
        raise ValueError("invalid image dimensions")
    points = np.float32([[0, 0], [width, 0], [width, height], [0, height]]).reshape(-1, 1, 2)
    projected_a = cv2.perspectiveTransform(points, a).reshape(-1, 2)
    projected_b = cv2.perspectiveTransform(points, b).reshape(-1, 2)
    if not np.isfinite(projected_a).all() or not np.isfinite(projected_b).all():
        raise ValueError("invalid projected loop")
    return float(np.max(np.linalg.norm(projected_a - projected_b, axis=1)))


def require_visual_loop(chained, direct, width, height, *, max_error_px=12.0):
    if not np.isfinite(max_error_px) or max_error_px <= 0:
        raise ValueError("invalid loop threshold")
    error = visual_loop_error(chained, direct, width, height)
    if error > max_error_px:
        raise ValueError("inconsistent visual loop closure")
    return error
