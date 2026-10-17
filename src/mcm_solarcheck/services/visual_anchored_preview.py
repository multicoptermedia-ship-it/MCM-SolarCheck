"""Single-warp visual RGB preview using original frames and one anchor.

Transforms are composed relative to frame zero; this is NOT bundle adjustment,
metric geometry, surveyed roof coverage or an orthophoto.
"""
from __future__ import annotations

from dataclasses import dataclass
import cv2
import numpy as np

from mcm_solarcheck.services.visual_frame_registration import estimate_visual_link
from mcm_solarcheck.services.visual_loop_consistency import require_visual_loop


@dataclass(frozen=True)
class AnchoredVisualPreview:
    image: np.ndarray
    pair_inliers: tuple[int, ...]
    preview_only: bool = True
    metric_orthophoto_verified: bool = False


def compose_anchored_visual_preview(frames, *, max_pixels=12_000_000, verify_loops=False, max_loop_error_px=12.0):
    frames = tuple(frames)
    if not 2 <= len(frames) <= 4:
        raise ValueError("expected 2-4 RGB frames")
    if type(max_pixels) is not int or max_pixels < 1:
        raise ValueError("invalid canvas limit")
    for frame in frames:
        if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3 or min(frame.shape[:2]) < 128:
            raise ValueError("invalid RGB frame")
    transforms = [np.eye(3, dtype=np.float64)]
    inliers = []
    for index in range(1, len(frames)):
        link, count = estimate_visual_link(frames[index - 1], frames[index])
        inverse = np.linalg.inv(link)
        current = transforms[-1] @ inverse
        if not np.isfinite(current).all():
            raise ValueError("nonfinite chained transform")
        transforms.append(current)
        inliers.append(count)
    if verify_loops:
        for index in range(2, len(frames)):
            try:
                direct, _ = estimate_visual_link(frames[index - 2], frames[index])
            except ValueError as exc:
                raise ValueError('cannot verify visual loop closure') from exc
            # Both transforms map frame index-2 into frame index coordinates.
            chained = np.linalg.inv(transforms[index]) @ transforms[index - 2]
            require_visual_loop(chained, direct, frames[index - 2].shape[1], frames[index - 2].shape[0], max_error_px=max_loop_error_px)
    all_corners = []
    for frame, h in zip(frames, transforms):
        height, width = frame.shape[:2]
        corners = np.float32([[0, 0], [width, 0], [width, height], [0, height]]).reshape(-1, 1, 2)
        projected = cv2.perspectiveTransform(corners, h).reshape(-1, 2)
        if not np.isfinite(projected).all():
            raise ValueError("invalid transformed corners")
        all_corners.append(projected)
    bounds = np.vstack(all_corners)
    low = np.floor(bounds.min(axis=0)).astype(int)
    high = np.ceil(bounds.max(axis=0)).astype(int)
    width, height = (high - low).tolist()
    if width <= 0 or height <= 0 or width * height > max_pixels:
        raise ValueError("visual preview exceeds canvas limit")
    offset = np.array([[1., 0., -low[0]], [0., 1., -low[1]], [0., 0., 1.]])
    accumulated = np.zeros((height, width, 3), dtype=np.float32)
    coverage = np.zeros((height, width), dtype=np.uint8)
    for frame, h in zip(frames, transforms):
        transform = offset @ h
        warped = cv2.warpPerspective(frame, transform, (width, height))
        mask = cv2.warpPerspective(np.ones(frame.shape[:2], np.uint8), transform, (width, height), flags=cv2.INTER_NEAREST)
        accumulated += warped.astype(np.float32) * mask[..., None]
        coverage += mask
    image = np.zeros((height, width, 3), dtype=np.uint8)
    valid = coverage > 0
    image[valid] = np.clip(accumulated[valid] / coverage[valid, None], 0, 255).astype(np.uint8)
    return AnchoredVisualPreview(image, tuple(inliers))
