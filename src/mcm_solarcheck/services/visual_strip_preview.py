"""Experimental bounded RGB preview strip, not an orthophoto or surveyed mosaic."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from mcm_solarcheck.services.visual_pair_mosaic import compose_visual_pair


@dataclass(frozen=True)
class VisualStripPreview:
    image: np.ndarray
    pair_inliers: tuple[int, ...]
    preview_only: bool = True
    metric_orthophoto_verified: bool = False


def compose_visual_strip(frames, *, max_frames=4, max_pixels=12_000_000):
    """Chain small RGB preview pairs; reject any weak intermediate alignment.

    Pairwise chaining can accumulate drift and MUST NOT be used for measurements.
    """
    frames = tuple(frames)
    if type(max_frames) is not int or not 2 <= max_frames <= 8:
        raise ValueError("invalid preview frame limit")
    if not 2 <= len(frames) <= max_frames:
        raise ValueError("preview requires 2 to max_frames RGB images")
    if type(max_pixels) is not int or max_pixels < 1:
        raise ValueError("invalid canvas limit")
    current = frames[0]
    inliers = []
    for frame in frames[1:]:
        result = compose_visual_pair(current, frame, max_pixels=max_pixels)
        current = result.image
        inliers.append(result.inliers)
    return VisualStripPreview(current, tuple(inliers))
