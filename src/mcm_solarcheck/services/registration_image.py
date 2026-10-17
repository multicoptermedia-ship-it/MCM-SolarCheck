"""Modality-independent feature input for non-metric image registration.

Thermal palette JPEGs may be used as VISUAL features, never temperatures.
"""
from __future__ import annotations

import cv2
import numpy as np


def registration_gray(frame):
    """Return an 8-bit feature image from grayscale, RGB or RGBA imagery."""
    if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8:
        raise ValueError("registration requires uint8 image")
    if frame.ndim == 2:
        gray = frame
    elif frame.ndim == 3 and frame.shape[2] in (3, 4):
        conversion = cv2.COLOR_RGB2GRAY if frame.shape[2] == 3 else cv2.COLOR_RGBA2GRAY
        gray = cv2.cvtColor(frame, conversion)
    else:
        raise ValueError("unsupported registration image channels")
    if min(gray.shape) < 128:
        raise ValueError("registration image too small")
    return np.ascontiguousarray(gray)
