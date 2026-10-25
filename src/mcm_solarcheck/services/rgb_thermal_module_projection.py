"""Ephemeral RGB-proposal to native thermal-pixel projection.

Consumes an EXTERNALLY validated pixel transform. No scale-by-resolution
heuristic, image import, database writes, module confirmation or temperature
calibration. A capture pair is not itself evidence of geometric registration.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import cv2
import numpy as np

from mcm_solarcheck.pairing.geometry import PixelTransform
from mcm_solarcheck.vision.polygon_geometry import is_valid_module_polygon

MAX_VERTICES = 24
MAX_THERMAL_PIXELS = 4_194_304
# Allowed descriptions name calibration methods; the flag and residual MUST be
# supported by separate, independent registration evidence at the call site.
ALLOWED_METHODS = frozenset({"calibrated_homography", "surveyed_plane_homography"})


@dataclass(frozen=True)
class ProjectedThermalPolygon:
    points_xy: tuple[tuple[float, float], ...]
    width: int
    height: int
    registration_error_px: float
    status: str = "unconfirmed_module_proposal"


def project_rgb_proposal_to_thermal(
    polygon_px: tuple[tuple[float, float], ...],
    transform: PixelTransform,
    *,
    max_registration_error_px: float = 2.0,
) -> ProjectedThermalPolygon:
    """Project an RGB proposal through an independently validated mapping.

    The transform's source grid is the RGB ORIGINAL IMAGE; target grid is the
    native thermal frame. RGB ORTHOPHOTO polygons require a separately derived
    ortho-to-thermal transform; this function never guesses one.
    """
    if not isinstance(transform, PixelTransform):
        raise TypeError("explicit RGB-to-thermal PixelTransform required")
    if transform.validated is not True or transform.matrix is None:
        raise ValueError("independently validated RGB/thermal registration required")
    if transform.method not in ALLOWED_METHODS:
        raise ValueError("calibrated/surveyed transform method required, not image resizing")
    dimensions = (
        transform.source_width, transform.source_height,
        transform.target_width, transform.target_height,
    )
    if any(type(value) is not int or value <= 0 for value in dimensions):
        raise ValueError("positive integral source/target dimensions required")
    if transform.target_width * transform.target_height > MAX_THERMAL_PIXELS:
        raise ValueError("thermal raster exceeds bounded diagnostic size")
    error = transform.validation_error_px
    if (
        type(max_registration_error_px) not in (float, int)
        or not isfinite(float(max_registration_error_px))
        or max_registration_error_px <= 0
        or type(error) not in (int, float)
        or not isfinite(float(error))
        or not 0 <= error <= max_registration_error_px
    ):
        raise ValueError("independent finite registration residual within limit required")
    try:
        rgb = np.asarray(polygon_px, dtype=np.float64)
        h = np.asarray(transform.matrix, dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise ValueError("finite polygon and transformation matrix required") from exc
    if (
        rgb.ndim != 2 or rgb.shape[1:] != (2,)
        or not 4 <= len(rgb) <= MAX_VERTICES
        or not np.isfinite(rgb).all()
        or not is_valid_module_polygon(rgb)
        or np.any(rgb[:, 0] < 0) or np.any(rgb[:, 1] < 0)
        or np.any(rgb[:, 0] >= transform.source_width)
        or np.any(rgb[:, 1] >= transform.source_height)
    ):
        raise ValueError("convex in-frame RGB module proposal required")
    if h.shape != (3, 3) or not np.isfinite(h).all():
        raise ValueError("finite 3x3 projective transform required")
    if abs(float(np.linalg.det(h))) < 1e-12:
        raise ValueError("singular projective transform")
    denominators = np.c_[rgb, np.ones(len(rgb))] @ h[2]
    if (
        np.any(np.abs(denominators) < 1e-9)
        or np.any(np.signbit(denominators) != np.signbit(denominators[0]))
    ):
        raise ValueError("projective horizon intersects proposal")
    projected = cv2.perspectiveTransform(rgb.reshape(-1, 1, 2), h).reshape(-1, 2)
    if not np.isfinite(projected).all() or np.any(np.abs(projected) > 1_000_000):
        raise ValueError("thermal projection is nonfinite or out of diagnostic bounds")
    if not is_valid_module_polygon(projected):
        raise ValueError("projected thermal proposal is degenerate")
    return ProjectedThermalPolygon(
        tuple((float(x), float(y)) for x, y in projected),
        transform.target_width, transform.target_height, float(error),
    )
