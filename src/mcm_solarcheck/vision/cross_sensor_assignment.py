"""Conservative Thermal -> RGB PV-module assignment.

A paired capture alone is insufficient.  A finding is projected into RGB only
through a validated PixelTransform and is assigned only when the projected
point is unambiguously inside one RGB module polygon.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from mcm_solarcheck.domain.models import PVModule
from mcm_solarcheck.pairing.geometry import PixelTransform
from mcm_solarcheck.vision.modules import point_in_polygon


@dataclass(frozen=True)
class CrossSensorModuleAssignment:
    module_id: str | None
    rgb_point: tuple[float, float] | None
    status: str
    transform_error_px: float | None
    candidates: tuple[str, ...] = ()


def _distance_to_segment(px: float, py: float, a: tuple[float,float], b: tuple[float,float]) -> float:
    ax, ay = a; bx, by = b
    dx, dy = bx-ax, by-ay
    denom = dx*dx + dy*dy
    if denom == 0:
        return hypot(px-ax, py-ay)
    t = max(0.0, min(1.0, ((px-ax)*dx + (py-ay)*dy) / denom))
    return hypot(px-(ax+t*dx), py-(ay+t*dy))


def distance_to_polygon_edge(x: float, y: float, polygon: tuple[tuple[float,float], ...]) -> float:
    if len(polygon) < 2:
        return 0.0
    return min(_distance_to_segment(x, y, polygon[i], polygon[(i+1) % len(polygon)]) for i in range(len(polygon)))


def assign_thermal_point_to_rgb_module(
    *,
    thermal_x: float,
    thermal_y: float,
    transform: PixelTransform,
    rgb_modules: tuple[PVModule, ...],
    rgb_frame_id: str,
    safety_factor: float = 1.0,
) -> CrossSensorModuleAssignment:
    """Map a thermal point to one RGB module, or refuse uncertain assignment."""
    if transform.source_width<=0 or transform.source_height<=0 or transform.target_width<=0 or transform.target_height<=0:
        return CrossSensorModuleAssignment(None,None,"invalid_transform_geometry",transform.validation_error_px)
    if safety_factor < 0:
        raise ValueError("safety_factor must be non-negative")
    if transform.validation_error_px is not None and transform.validation_error_px < 0:
        return CrossSensorModuleAssignment(None,None,"invalid_transform_error",transform.validation_error_px)
    if not transform.validated or transform.matrix is None:
        return CrossSensorModuleAssignment(None, None, "transform_unvalidated", transform.validation_error_px)

    x, y = transform.map_point(thermal_x, thermal_y)
    if x < 0 or y < 0 or x >= transform.target_width or y >= transform.target_height:
        return CrossSensorModuleAssignment(None, (x,y), "outside_rgb", transform.validation_error_px)

    matches = tuple(sorted(
        (m for m in rgb_modules if m.frame_id == rgb_frame_id and point_in_polygon(x, y, m.polygon_px)),
        key=lambda m: m.module_id,
    ))
    if not matches:
        return CrossSensorModuleAssignment(None, (x,y), "no_module", transform.validation_error_px)
    if len(matches) > 1:
        return CrossSensorModuleAssignment(None, (x,y), "ambiguous_overlap", transform.validation_error_px, tuple(m.module_id for m in matches))

    module = matches[0]
    uncertainty = (transform.validation_error_px or 0.0) * safety_factor
    edge_distance = distance_to_polygon_edge(x, y, module.polygon_px)
    if edge_distance <= uncertainty:
        return CrossSensorModuleAssignment(None, (x,y), "ambiguous_edge", transform.validation_error_px, (module.module_id,))

    return CrossSensorModuleAssignment(module.module_id, (x,y), "assigned", transform.validation_error_px, (module.module_id,))
