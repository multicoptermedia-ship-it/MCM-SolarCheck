"""Bounded, non-metric overlap disagreement diagnostics for visual mosaics."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class VisualOverlapQuality:
    covered_pixels: int
    multiply_covered_pixels: int
    mean_overlap_disagreement: float | None
    max_overlap_disagreement: float | None
    metric_accuracy_verified: bool = False


def assess_visual_overlap(warped_frames, masks):
    """Compare co-visible uint8 images, without interpreting pixel differences as geometry.

    Values are mean absolute intensity differences (0..255), not reprojection
    errors, temperature differences, or proof of alignment.
    """
    images, masks = tuple(warped_frames), tuple(masks)
    if not 2 <= len(images) == len(masks) <= 8:
        raise ValueError("invalid visual overlap count")
    shape = images[0].shape
    if len(shape) not in (2, 3) or (len(shape) == 3 and shape[2] not in (1, 3, 4)):
        raise ValueError("invalid image layout")
    if any(im.shape != shape or im.dtype != np.uint8 for im in images):
        raise ValueError("incompatible visual images")
    if any(mask.shape != shape[:2] or mask.dtype != np.uint8 for mask in masks):
        raise ValueError("invalid overlap masks")
    if any(not np.isin(mask, [0, 1]).all() for mask in masks):
        raise ValueError("overlap masks must be binary")
    counts = np.zeros(shape[:2], dtype=np.uint8)
    total = np.zeros(shape, dtype=np.float32)
    for im, mask in zip(images, masks):
        active = mask != 0
        counts += active.astype(np.uint8)
        if len(shape) == 3:
            total += im.astype(np.float32) * active[..., None]
        else:
            total += im.astype(np.float32) * active
    covered = int(np.count_nonzero(counts))
    overlap = counts > 1
    multi = int(np.count_nonzero(overlap))
    if multi == 0:
        return VisualOverlapQuality(covered, 0, None, None)
    denominator = np.maximum(counts, 1)
    if len(shape) == 3:
        average = total / denominator[..., None]
    else:
        average = total / denominator
    # Average deviation of participating samples from the overlap mean.
    disagreements = np.zeros(shape[:2], dtype=np.float32)
    for im, mask in zip(images, masks):
        deviation = np.abs(im.astype(np.float32) - average)
        if len(shape) == 3:
            deviation = deviation.mean(axis=2)
        disagreements += deviation * (mask != 0)
    disagreements[overlap] /= counts[overlap]
    return VisualOverlapQuality(covered, multi,
                                float(disagreements[overlap].mean()),
                                float(disagreements[overlap].max()))
