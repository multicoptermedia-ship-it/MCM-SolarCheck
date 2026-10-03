"""PV-module detection boundary and pixel-space finding assignment."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from mcm_solarcheck.domain.models import Finding, ImageFrame, PVModule


class PVModuleDetector(Protocol):
    @property
    def name(self) -> str: ...

    def detect(self, frame: ImageFrame) -> tuple[PVModule, ...]: ...


def point_in_polygon(x: float, y: float, polygon: tuple[tuple[float, float], ...]) -> bool:
    """Ray-casting point-in-polygon test in image pixel coordinates."""
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def assign_findings_to_modules(
    findings: tuple[Finding, ...],
    modules: tuple[PVModule, ...],
) -> tuple[Finding, ...]:
    """Assign findings to detected module polygons in the same frame.

    Ambiguous overlaps are not silently resolved: the highest-confidence module
    wins only when confidence is available; otherwise the first deterministic
    module-id order is used and the ambiguity is recorded in metadata.
    """
    ordered_modules = tuple(sorted(modules, key=lambda m: m.module_id))
    assigned: list[Finding] = []
    for finding in findings:
        matches = [m for m in ordered_modules if m.frame_id == finding.thermal_frame_id and
                   point_in_polygon(finding.pixel_x, finding.pixel_y, m.polygon_px)]
        if not matches:
            assigned.append(finding)
            continue
        matches.sort(key=lambda m: (-(m.detection_confidence or -1.0), m.module_id))
        chosen = matches[0]
        metadata = dict(finding.metadata)
        if len(matches) > 1:
            metadata["module_assignment_ambiguous"] = "true"
            metadata["module_assignment_candidates"] = ",".join(m.module_id for m in matches)
        assigned.append(replace(finding, module_id=chosen.module_id, metadata=metadata))
    return tuple(assigned)
