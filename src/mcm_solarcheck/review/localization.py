"""Module-level service localization for inspection findings.

A field technician needs the physical module identity, not an invented
pixel-to-ground coordinate for the hotspot itself. Frame GPS/RTK remains
provenance evidence only.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.domain.models import Finding


@dataclass(frozen=True)
class FindingLocation:
    finding_id: str
    module_id: str | None
    status: str
    gps_scope: str


def localize_finding(finding: Finding) -> FindingLocation:
    """Resolve service localization at module granularity only."""
    if finding.module_id is None or not finding.module_id.strip():
        return FindingLocation(finding.finding_id, None, "module_unresolved", "frame_evidence" if finding.position is not None else "none")
    return FindingLocation(
        finding.finding_id,
        finding.module_id,
        "module_resolved",
        "frame_evidence" if finding.position is not None else "none",
    )
