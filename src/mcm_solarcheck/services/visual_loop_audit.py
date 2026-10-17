"""Offline multi-overlap registration diagnostics; non-metric pixel coordinates."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from mcm_solarcheck.services.visual_frame_registration import estimate_visual_link
from mcm_solarcheck.services.visual_loop_consistency import visual_loop_error


@dataclass(frozen=True)
class VisualLoopFinding:
    start_index: int
    end_index: int
    direct_inliers: int
    max_corner_error_px: float
    passes: bool


def audit_visual_loops(frames, *, max_error_px=12.0, max_frames=8):
    """Compare independent direct links against adjacent-link compositions.

    Unavailable direct matches are explicitly reported as unverifiable, not passing.
    """
    frames = tuple(frames)
    if not 3 <= len(frames) <= max_frames or max_frames > 8:
        raise ValueError("requires 3-8 RGB frames")
    if not np.isfinite(max_error_px) or max_error_px <= 0:
        raise ValueError("invalid loop threshold")
    adjacent = []
    for i in range(len(frames) - 1):
        h, _ = estimate_visual_link(frames[i], frames[i + 1])
        adjacent.append(h)
    findings = []
    for start in range(len(frames) - 2):
        for end in range(start + 2, len(frames)):
            chained = np.eye(3)
            for index in range(start, end):
                chained = adjacent[index] @ chained
            try:
                direct, inliers = estimate_visual_link(frames[start], frames[end])
                error = visual_loop_error(chained, direct, frames[start].shape[1], frames[start].shape[0])
                findings.append(VisualLoopFinding(start, end, inliers, error, error <= max_error_px))
            except ValueError:
                findings.append(VisualLoopFinding(start, end, 0, float("nan"), False))
    return tuple(findings)
