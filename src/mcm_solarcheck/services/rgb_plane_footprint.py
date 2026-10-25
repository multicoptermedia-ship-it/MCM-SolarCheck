"""Geometric area correction for inclined PV roof/module planes.

A horizontal ground orthoprojection foreshortens a surveyed plane. This
factor is an area geometry relationship, not a way to reconstruct camera
poses, measure roofs from a JPEG, or declare a verified orthophoto.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, isfinite
import numpy as np

from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D


@dataclass(frozen=True)
class RGBPlaneFootprint:
    tilt_from_horizontal_deg: float
    horizontal_to_surface_area_factor: float
    horizontal_fraction_of_true_surface: float
    vertical_projection_possible: bool
    georeferencing_verified: bool = False


def inspect_rgb_plane_footprint(plane: SurveyedPlane3D) -> RGBPlaneFootprint:
    """Derive projection area factors from a surveyed ENU plane normal."""
    if not isinstance(plane, SurveyedPlane3D):
        raise TypeError("explicit independently established plane required")
    normal = np.asarray(plane.normal_enu, dtype=np.float64)
    origin = np.asarray(plane.point_enu_m, dtype=np.float64)
    if normal.shape != (3,) or origin.shape != (3,) or not np.isfinite(normal).all() or not np.isfinite(origin).all():
        raise ValueError("finite ENU plane required")
    if not np.isclose(np.linalg.norm(normal), 1., atol=1e-6) or normal[2] < 0:
        raise ValueError("unit upward-facing plane normal required")
    nz = float(np.clip(normal[2], 0., 1.))
    tilt = degrees(acos(nz))
    if nz < 1e-8:
        return RGBPlaneFootprint(float(tilt), float("inf"), nz, False)
    return RGBPlaneFootprint(float(tilt), 1.0 / nz, nz, True)
