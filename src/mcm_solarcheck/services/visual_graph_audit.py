"""Shared RGB/thermal-display graph diagnostics from independent image links."""
from __future__ import annotations

from dataclasses import dataclass
import cv2
import numpy as np

from mcm_solarcheck.services.registration_image import registration_gray
from mcm_solarcheck.services.visual_frame_registration import estimate_visual_link
from mcm_solarcheck.services.visual_translation_graph import solve_translation_graph


@dataclass(frozen=True)
class VisualGraphAudit:
    frame_count: int
    accepted_edges: tuple[tuple[int, int], ...]
    missing_edges: tuple[tuple[int, int], ...]
    rms_residual_px: float
    preview_only: bool = True
    metric_orthophoto_verified: bool = False


def audit_visual_translation_graph(frames, *, max_frames=8, max_rms_px=12.0):
    """Compare all reliably matched links via a translation-only graph.

    The homography displacement of the source image center is an approximation,
    not a calibrated camera displacement or a metric measurement.
    """
    frames = tuple(frames)
    if not 3 <= len(frames) <= max_frames <= 8:
        raise ValueError("requires 3-8 visual frames")
    for frame in frames:
        registration_gray(frame)
    edges, accepted, missing = [], [], []
    for i in range(len(frames)):
        for j in range(i + 1, len(frames)):
            try:
                h, inliers = estimate_visual_link(frames[i], frames[j])
            except ValueError:
                missing.append((i, j))
                continue
            height, width = frames[i].shape[:2]
            center = np.float32([[[width / 2., height / 2.]]])
            transformed = cv2.perspectiveTransform(center, h)[0, 0]
            delta = transformed - center[0, 0]
            if not np.isfinite(delta).all():
                missing.append((i, j))
                continue
            edges.append((i, j, float(delta[0]), float(delta[1]), float(min(inliers, 500))))
            accepted.append((i, j))
    graph = solve_translation_graph(len(frames), edges, max_frames=max_frames, max_rms_px=max_rms_px)
    return VisualGraphAudit(len(frames), tuple(accepted), tuple(missing), graph.rms_residual_px)
