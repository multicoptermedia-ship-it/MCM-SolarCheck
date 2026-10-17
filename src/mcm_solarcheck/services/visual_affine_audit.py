"""Conservative affine-only visual graph from shared RGB/thermal registration."""
from __future__ import annotations

import numpy as np

from mcm_solarcheck.services.registration_image import registration_gray
from mcm_solarcheck.services.visual_frame_registration import estimate_visual_link
from mcm_solarcheck.services.visual_affine_graph import fit_affine_graph


def audit_visual_affine_graph(frames, *, max_frames=8, max_error=0.1,
                              perspective_tolerance=1e-7):
    """Estimate pair links, accepting only verified affine-like homographies.

    Reject unsupported perspective links rather than silently flattening them.
    """
    frames = tuple(frames)
    if not 3 <= len(frames) <= max_frames <= 8:
        raise ValueError("requires 3-8 visual frames")
    if not np.isfinite(perspective_tolerance) or perspective_tolerance <= 0:
        raise ValueError("invalid perspective tolerance")
    for frame in frames:
        registration_gray(frame)
    links = []
    for i in range(len(frames)):
        for j in range(i + 1, len(frames)):
            try:
                h, inliers = estimate_visual_link(frames[i], frames[j])
            except ValueError:
                continue
            h = np.asarray(h, dtype=np.float64)
            h = h / h[2, 2]
            if not np.allclose(h[2], [0., 0., 1.], rtol=0., atol=perspective_tolerance):
                raise ValueError("perspective geometry requires projective optimization")
            links.append((i, j, h, float(min(inliers, 500))))
    return fit_affine_graph(len(frames), links, max_frames=max_frames, max_error=max_error)
