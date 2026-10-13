"""Explicit partial-coverage handoff; unmatched thermal evidence is never silently dropped."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import (
    ImportedCandidateAnalysis, IncompleteImportError,
)


@dataclass(frozen=True)
class PartialM3TAnalysis:
    paired_analysis: ImportedCandidateAnalysis
    unpaired_thermal_frame_ids: tuple[str, ...]
    unpaired_rgb_frame_ids: tuple[str, ...]
    completeness: str = "partial_rgb_thermal_coverage"


def analyze_partial_m3t_project(
    imported: ProjectImportResult, *, acknowledge_incomplete_coverage: bool = False
) -> PartialM3TAnalysis:
    if not isinstance(imported, ProjectImportResult):
        raise TypeError("ProjectImportResult required")
    if acknowledge_incomplete_coverage is not True:
        raise IncompleteImportError("partial coverage requires explicit acknowledgement")
    if imported.thermal_batch.failures:
        raise IncompleteImportError("thermal import failures require manual resolution")
    thermal_ids = [r.frame.frame_id for r in imported.thermal_batch.results]
    rgb_ids = [r.frame_id for r in imported.rgb_frames]
    if len(set(thermal_ids)) != len(thermal_ids) or len(set(rgb_ids)) != len(rgb_ids):
        raise IncompleteImportError("duplicate frame IDs")
    paired_t = {p.thermal_frame_id for p in imported.pairs}
    paired_r = {p.rgb_frame_id for p in imported.pairs}
    if not imported.pairs or not paired_t <= set(thermal_ids) or not paired_r <= set(rgb_ids):
        raise IncompleteImportError("invalid or missing image pairs")
    if len(paired_t) != len(imported.pairs) or len(paired_r) != len(imported.pairs):
        raise IncompleteImportError("ambiguous image pairing")
    findings: list[Finding] = []
    for result in imported.thermal_batch.results:
        if result.frame.frame_id in paired_t:
            findings.extend(result.findings)
    return PartialM3TAnalysis(
        paired_analysis=ImportedCandidateAnalysis(
            paired_frames=len(imported.pairs),
            imported_thermal_frames=len(paired_t),
            candidates=tuple(findings),
            source="m3t_importer_candidates_unverified_partial_coverage",
        ),
        unpaired_thermal_frame_ids=tuple(sorted(set(thermal_ids) - paired_t)),
        unpaired_rgb_frame_ids=tuple(sorted(set(rgb_ids) - paired_r)),
    )
