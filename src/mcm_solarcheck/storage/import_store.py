"""Persistence bridge from M3T import results into project storage."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.importers.batch import M3TBatchResult
from .sqlite import ProjectDatabase


@dataclass(frozen=True)
class PersistenceSummary:
    frames_saved: int
    findings_saved: int
    import_failures: int


def store_m3t_batch(
    database: ProjectDatabase,
    project_id: str,
    batch: M3TBatchResult,
) -> PersistenceSummary:
    """Store all successful frame imports and their reviewable findings."""
    frames = 0
    findings = 0
    for result in batch.results:
        database.save_thermal_frame(project_id, result.frame, result.quality)
        database.save_findings(project_id, result.findings)
        frames += 1
        findings += len(result.findings)
    return PersistenceSummary(frames, findings, len(batch.failures))
