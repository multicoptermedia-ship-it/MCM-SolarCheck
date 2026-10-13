"""Read-only analysis handoff from actual DJI M3T importer findings.

Candidates are importer output, not validated PV defects or a trained model.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.domain.models import Finding


@dataclass(frozen=True)
class ImportedCandidateAnalysis:
    paired_frames: int
    imported_thermal_frames: int
    candidates: tuple[Finding, ...]
    source: str = "m3t_importer_candidates_unverified"


class IncompleteImportError(ValueError):
    """Imported evidence is incomplete or not paired for inspection."""


def analyze_imported_m3t_candidates(imported: object) -> ImportedCandidateAnalysis:
    if not isinstance(imported, ProjectImportResult):
        raise TypeError("ProjectImportResult required")
    if imported.thermal_batch.failures:
        raise IncompleteImportError("thermal import failures require manual resolution")
    if not imported.pairs or not imported.thermal_batch.results:
        raise IncompleteImportError("paired RGB and thermal evidence required")
    paired_thermal_ids = {pair.thermal_frame_id for pair in imported.pairs}
    candidates = []
    for result in imported.thermal_batch.results:
        if result.frame.frame_id in paired_thermal_ids:
            candidates.extend(result.findings)
    if len(paired_thermal_ids) != len(imported.thermal_batch.results):
        raise IncompleteImportError("unpaired thermal frames require manual resolution")
    return ImportedCandidateAnalysis(
        paired_frames=len(imported.pairs),
        imported_thermal_frames=len(imported.thermal_batch.results),
        candidates=tuple(candidates),
    )
