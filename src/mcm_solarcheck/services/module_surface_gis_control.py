"""Audit an independently supplied local-module-to-projected-CRS affine.

An affine fit alone is not georeferencing certification or GeoTIFF export.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class SurfaceGISControlAudit:
    rms_error_m: float
    max_error_m: float
    tolerance_m: float
    control_count: int
    within_tolerance: bool
    independently_verified: bool = False


def audit_surface_gis_controls(
    surface_uv_m: np.ndarray,
    surveyed_crs_xy_m: np.ndarray,
    *,
    tolerance_m: float,
) -> tuple[tuple[float, float, float, float, float, float], SurfaceGISControlAudit]:
    """Least-squares affine with residual checks; caller supplies real surveyed controls.

    CRS must be independently established as projected metric; never infer EPSG
    from ENU, DJI GPS or these arrays. Output is diagnostic, not export authority.
    """
    if isinstance(tolerance_m, bool) or not isinstance(tolerance_m, (int, float)) or not np.isfinite(tolerance_m) or tolerance_m <= 0:
        raise ValueError("positive finite control tolerance required")
    uv = np.asarray(surface_uv_m, dtype=np.float64)
    xy = np.asarray(surveyed_crs_xy_m, dtype=np.float64)
    if uv.ndim != 2 or xy.ndim != 2 or uv.shape != xy.shape or uv.shape[1:] != (2,) or len(uv) < 4:
        raise ValueError("at least four paired surface and surveyed GIS controls required")
    if not np.isfinite(uv).all() or not np.isfinite(xy).all():
        raise ValueError("finite GIS controls required")
    if len(np.unique(uv, axis=0)) != len(uv) or len(np.unique(xy, axis=0)) != len(xy):
        raise ValueError("duplicate GIS control points")
    centered = uv - uv.mean(axis=0)
    singular = np.linalg.svd(centered, compute_uv=False)
    if singular[0] <= 0 or singular[1] / singular[0] < 1e-6:
        raise ValueError("GIS controls must span a two-dimensional area")
    design = np.column_stack((uv, np.ones(len(uv))))
    coefficients, _, rank, _ = np.linalg.lstsq(design, xy, rcond=None)
    if rank != 3 or not np.isfinite(coefficients).all():
        raise ValueError("invalid GIS affine fit")
    predicted = design @ coefficients
    errors = np.linalg.norm(predicted - xy, axis=1)
    rms = float(np.sqrt(np.mean(errors ** 2)))
    maximum = float(np.max(errors))
    if not np.isfinite(rms) or not np.isfinite(maximum):
        raise ValueError("nonfinite GIS control residuals")
    a, d = coefficients[0]
    b, e = coefficients[1]
    c, f = coefficients[2]
    if not np.isfinite(a * e - b * d) or abs(a * e - b * d) <= 1e-12:
        raise ValueError("singular GIS affine transform")
    return (float(a), float(b), float(c), float(d), float(e), float(f)), SurfaceGISControlAudit(
        rms, maximum, float(tolerance_m), len(uv), maximum <= tolerance_m
    )
