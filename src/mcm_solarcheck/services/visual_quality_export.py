"""Serializable non-metric visual preview quality, without private flight metadata."""
from __future__ import annotations

import json
import math


def projective_quality_summary(result):
    """Return a bounded, privacy-minimal machine-readable quality summary."""
    q = result.overlap_quality
    if q is None:
        raise ValueError("projective overlap quality is unavailable")
    rms = float(result.rms_corner_error_px)
    if not math.isfinite(rms) or rms < 0:
        raise ValueError("invalid projective RMS")
    for value in (q.mean_overlap_disagreement, q.max_overlap_disagreement):
        if value is not None and (not math.isfinite(float(value)) or not 0 <= value <= 255):
            raise ValueError("invalid visual overlap disagreement")
    if not 0 <= q.multiply_covered_pixels <= q.covered_pixels:
        raise ValueError("invalid visual overlap coverage")
    return {
        "schema_version": 1,
        "preview_only": True,
        "metric_orthophoto_verified": False,
        "temperature_calibrated": False,
        "rms_corner_error_px": rms,
        "covered_pixels": int(q.covered_pixels),
        "multiply_covered_pixels": int(q.multiply_covered_pixels),
        "mean_overlap_disagreement_0_255": q.mean_overlap_disagreement,
        "max_overlap_disagreement_0_255": q.max_overlap_disagreement,
    }


def projective_quality_json(result):
    return json.dumps(projective_quality_summary(result), sort_keys=True, indent=2) + "\n"
