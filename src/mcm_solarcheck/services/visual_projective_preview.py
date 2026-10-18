"""Render a bounded non-metric preview from globally refined projective links.

Works with uint8 RGB and single-channel thermal-display images. Never Celsius.
"""
from __future__ import annotations

from dataclasses import dataclass
import cv2
import numpy as np

from mcm_solarcheck.services.registration_image import registration_gray
from mcm_solarcheck.services.visual_projective_audit import audit_visual_projective_graph


@dataclass(frozen=True)
class ProjectiveVisualPreview:
    image: np.ndarray
    rms_corner_error_px: float
    pair_inliers: tuple[int, ...] = ()
    preview_only: bool = True
    metric_orthophoto_verified: bool = False


def compose_projective_visual_preview(frames, *, max_pixels=12_000_000, max_rms_px=12.):
    """Warp each original image once into the optimized frame-zero reference."""
    frames = tuple(frames)
    if not 3 <= len(frames) <= 4:
        raise ValueError("requires 3-4 visual frames")
    for frame in frames:
        registration_gray(frame)
    if len({frame.ndim for frame in frames}) != 1 or (
            frames[0].ndim == 3 and len({frame.shape[2] for frame in frames}) != 1):
        raise ValueError("mixed image channel layouts")
    if type(max_pixels) is not int or max_pixels < 1:
        raise ValueError("invalid canvas limit")
    fit = audit_visual_projective_graph(frames, max_rms_px=max_rms_px)
    corners = []
    for frame, h in zip(frames, fit.transforms_to_anchor):
        height, width = frame.shape[:2]
        points = np.float32([[0, 0], [width, 0], [width, height], [0, height]]).reshape(-1, 1, 2)
        projected = cv2.perspectiveTransform(points, h).reshape(-1, 2)
        if not np.isfinite(projected).all() or np.max(np.abs(projected)) > 1e6:
            raise ValueError("invalid projected bounds")
        corners.append(projected)
    bounds = np.vstack(corners)
    low = np.floor(bounds.min(axis=0)).astype(np.int64)
    high = np.ceil(bounds.max(axis=0)).astype(np.int64)
    width, height = (high - low).tolist()
    if width <= 0 or height <= 0 or width * height > max_pixels:
        raise ValueError("projective preview exceeds canvas limit")
    offset = np.array([[1., 0., -low[0]], [0., 1., -low[1]], [0., 0., 1.]])
    channels = 1 if frames[0].ndim == 2 else frames[0].shape[2]
    total = np.zeros((height, width, channels), dtype=np.float32)
    coverage = np.zeros((height, width), dtype=np.uint16)
    for frame, h in zip(frames, fit.transforms_to_anchor):
        transform = offset @ h
        warped = cv2.warpPerspective(frame, transform, (width, height))
        if warped.ndim == 2:
            warped = warped[:, :, None]
        mask = cv2.warpPerspective(np.ones(frame.shape[:2], dtype=np.uint8),
                                   transform, (width, height), flags=cv2.INTER_NEAREST)
        total += warped.astype(np.float32) * mask[:, :, None]
        coverage += mask
    result = np.zeros_like(total, dtype=np.uint8)
    valid = coverage > 0
    result[valid] = np.clip(total[valid] / coverage[valid, None], 0, 255).astype(np.uint8)
    if channels == 1:
        result = result[:, :, 0]
    return ProjectiveVisualPreview(result, fit.rms_corner_error_px)
