"""Bounded nonmetric RGB segment canvas planning without decoding originals."""
import math
import numpy as np


def plan_rgb_canvas(segment, dimensions, *, max_pixels=12_000_000):
    """Plan pixel bounds for a contiguous segment using registered corner positions.

    dimensions maps capture keys to (width, height) of working images.
    This is a nonmetric plan; no orthophoto or mosaic is claimed.
    """
    if type(max_pixels) is not int or max_pixels < 1:
        raise ValueError("invalid canvas pixel limit")
    frames = segment["frames"]
    if not frames:
        raise ValueError("empty RGB segment")
    corners = []
    for key, raw in frames.items():
        if key not in dimensions:
            raise ValueError("missing RGB dimensions")
        width, height = dimensions[key]
        if type(width) is not int or type(height) is not int or width < 1 or height < 1:
            raise ValueError("invalid RGB dimensions")
        h = np.asarray(raw, dtype=np.float64)
        if h.shape != (3, 3) or not np.isfinite(h).all():
            raise ValueError("invalid RGB transform")
        pts = np.array([[0, 0, 1], [width, 0, 1],
                        [width, height, 1], [0, height, 1]], dtype=np.float64).T
        if abs(np.linalg.det(h)) < 1e-12:
            raise ValueError("singular RGB transform")
        mapped = np.linalg.inv(h) @ pts
        if np.any(np.abs(mapped[2]) < 1e-9):
            raise ValueError("unbounded projective geometry")
        xy = mapped[:2] / mapped[2]
        if not np.isfinite(xy).all():
            raise ValueError("nonfinite canvas bounds")
        corners.extend(xy.T.tolist())
    array = np.asarray(corners)
    left, top = np.floor(array.min(axis=0)).astype(int)
    right, bottom = np.ceil(array.max(axis=0)).astype(int)
    width, height = int(right - left), int(bottom - top)
    if width < 1 or height < 1 or width * height > max_pixels:
        raise ValueError("RGB canvas exceeds pixel limit")
    return {"origin": [int(left), int(top)], "width": width, "height": height,
            "pixel_count": width * height, "nonmetric": True}
