"""Persistence bridge from M3T import results into project storage."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from mcm_solarcheck.importers.batch import M3TBatchResult
from mcm_solarcheck.importers.project import ProjectImportResult
from .sqlite import ProjectDatabase

@dataclass(frozen=True)
class PersistenceSummary:
    frames_saved:int
    findings_saved:int
    import_failures:int

def store_m3t_batch(database:ProjectDatabase,project_id:str,batch:M3TBatchResult,*,heartbeat:Callable[[],None]|None=None)->PersistenceSummary:
    """Store each successful frame and its findings in one transaction."""
    frames=findings=0
    for result in batch.results:
        database.save_thermal_result(project_id,result.frame,result.quality,result.findings)
        frames+=1;findings+=len(result.findings)
        if heartbeat is not None:
            heartbeat()
    return PersistenceSummary(frames,findings,len(batch.failures))


def store_project_import(
    database: ProjectDatabase,
    customer_id: str,
    project_id: str,
    imported: ProjectImportResult,
    *,
    heartbeat: Callable[[], None] | None = None,
) -> PersistenceSummary:
    """Persist the thermal portion of a validated customer project import.

    Customer ownership is enforced by the processing service before this
    persistence boundary is reached. The project identifier remains the
    storage key used by ProjectDatabase.
    """
    if not customer_id.strip() or not project_id.strip():
        raise ValueError("customer and project are required")
    return store_m3t_batch(database, project_id.strip(), imported.thermal_batch, heartbeat=heartbeat)
