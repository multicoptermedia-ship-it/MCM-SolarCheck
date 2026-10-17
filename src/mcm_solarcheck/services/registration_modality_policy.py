"""Explicit modality policy for shared visual registration.

The same algorithm can run within RGB or within thermal-display frames.
Cross-camera alignment is a separate calibrated problem.
"""
from __future__ import annotations


def require_same_modality(modalities):
    """Reject mixed RGB/thermal series before any shared registration job."""
    values = tuple(modalities)
    if len(values) < 2 or any(v not in ("rgb", "thermal_visual") for v in values):
        raise ValueError("unsupported visual registration modality")
    if len(set(values)) != 1:
        raise ValueError("cross-camera RGB/thermal registration requires calibration")
    return values[0]
