"""Shared RGB/thermal-display entrypoint for non-metric projective graph audit."""
from __future__ import annotations

from mcm_solarcheck.services.registration_image import registration_gray
from mcm_solarcheck.services.visual_frame_registration import estimate_visual_link
from mcm_solarcheck.services.visual_projective_graph import fit_projective_graph
from mcm_solarcheck.services.visual_graph_coverage import require_redundant_visual_graph


def audit_visual_projective_graph(frames, *, max_frames=8, max_rms_px=12., require_redundancy=False):
    """Build all verifiable pair links and refine transforms to first image.

    Missing direct overlaps are tolerated only when the remaining graph connects.
    """
    frames = tuple(frames)
    if not 3 <= len(frames) <= max_frames <= 8:
        raise ValueError("requires 3-8 visual frames")
    for frame in frames:
        registration_gray(frame)
    links = []
    for i in range(len(frames)):
        for j in range(i + 1, len(frames)):
            try:
                h, inliers = estimate_visual_link(frames[i], frames[j])
            except ValueError:
                continue
            links.append((i, j, h, float(min(inliers, 500))))
    if require_redundancy:
        require_redundant_visual_graph(len(frames), [(i, j) for i, j, _, _ in links])
    return fit_projective_graph([frame.shape[:2] for frame in frames], links,
                                max_frames=max_frames, max_rms_px=max_rms_px)
