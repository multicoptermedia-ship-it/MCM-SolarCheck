"""Module-level service localization for inspection findings.

A field technician needs the physical module identity, not an invented
pixel-to-ground coordinate for the hotspot itself. Frame GPS/RTK remains
provenance evidence only.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from mcm_solarcheck.domain.models import Finding


@dataclass(frozen=True)
class FindingLocation:
    finding_id: str
    module_id: str | None
    status: str
    gps_scope: str


def localize_finding(finding: Finding) -> FindingLocation:
    """Resolve service localization at module granularity only."""
    gps_scope = "none"
    if finding.position is not None and all(isfinite(float(v)) for v in (finding.position.latitude, finding.position.longitude)) and -90 <= finding.position.latitude <= 90 and -180 <= finding.position.longitude <= 180:
        gps_scope = "frame_evidence"
    if finding.module_id is None or not finding.module_id.strip():
        return FindingLocation(finding.finding_id, None, "module_unresolved", gps_scope)
    return FindingLocation(
        finding.finding_id,
        finding.module_id,
        "module_resolved",
        gps_scope,
    )
