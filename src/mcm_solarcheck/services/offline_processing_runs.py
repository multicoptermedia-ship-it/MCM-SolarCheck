"""Conservative persisted lifecycle for a future offline processing worker.

There is intentionally NO mark-completed entry point here: importing images or
calculating preliminary candidates cannot make an expert-review-ready result.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from mcm_solarcheck.services.offline_processing_inventory import (
    capture_offline_processing_inventory,
)


@dataclass(frozen=True)
class OfflineProcessingRun:
    project_id: str
    run_id: str
    status: str
    input_fingerprint: str
    pipeline_version: str
    expected_thermal_frames: int
    processed_thermal_frames: int
    failed_thermal_frames: int
    stale_inputs: bool


def _read_record(row, *, stale: bool) -> OfflineProcessingRun:
    return OfflineProcessingRun(
        project_id=row["project_id"],
        run_id=row["run_id"],
        status=row["status"],
        input_fingerprint=row["input_fingerprint"],
        pipeline_version=row["pipeline_version"],
        expected_thermal_frames=row["expected_thermal_frames"],
        processed_thermal_frames=row["processed_thermal_frames"],
        failed_thermal_frames=row["failed_thermal_frames"],
        stale_inputs=stale,
    )


def latest_offline_processing_run(database, project_id: str) -> OfflineProcessingRun | None:
    """Read only one project's latest run and compare its stored input digest."""
    snapshot = capture_offline_processing_inventory(database, project_id)
    with database.connect() as sql:
        row = sql.execute(
            "SELECT * FROM offline_processing_runs WHERE project_id=? "
            "ORDER BY created_at DESC, rowid DESC LIMIT 1", (project_id,),
        ).fetchone()
    if row is None:
        return None
    return _read_record(
        row, stale=row["input_fingerprint"] != snapshot.fingerprint,
    )


def begin_offline_processing_run(
    database, project_id: str, *, pipeline_version: str,
) -> OfflineProcessingRun:
    """Reserve one run atomically, without invoking or claiming a processor.

    For use by a future trusted processing worker, not a GUI 'done' action.
    """
    if (not isinstance(pipeline_version, str)
            or not 1 <= len(pipeline_version.strip()) <= 120):
        raise ValueError("explicit processing pipeline version is required")
    with database.connect() as sql:
        sql.execute("BEGIN IMMEDIATE")
        # The reserved write lock prevents an import from changing this
        # inventory between fingerprinting and persisting the planned job.
        snapshot = capture_offline_processing_inventory(database, project_id)
        if not snapshot.can_plan_processing:
            raise ValueError("thermal inputs are required for processing")
        if sql.execute(
            "SELECT 1 FROM offline_processing_runs WHERE project_id=? "
            "AND status='running'", (project_id,),
        ).fetchone() is not None:
            raise ValueError("processing run already active for this project")
        run_id = uuid4().hex
        sql.execute(
            "INSERT INTO offline_processing_runs "
            "(run_id,project_id,input_fingerprint,pipeline_version,status,"
            "expected_thermal_frames) VALUES (?,?,?,?,?,?)",
            (run_id, project_id, snapshot.fingerprint,
             pipeline_version.strip(), "running", snapshot.thermal_frames),
        )
    result = latest_offline_processing_run(database, project_id)
    assert result is not None
    return result


def stop_offline_processing_run(
    database, project_id: str, run_id: str, *, outcome: str,
    processed_thermal_frames: int = 0, failed_thermal_frames: int = 0,
) -> None:
    """Record failure/cancellation atomically; no implicit 'completed' path."""
    if outcome not in ("failed", "cancelled"):
        raise ValueError("only failed or cancelled outcomes are permitted")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("processing run ID required")
    if (type(processed_thermal_frames) is not int
            or type(failed_thermal_frames) is not int
            or min(processed_thermal_frames, failed_thermal_frames) < 0):
        raise ValueError("non-negative integer progress counts required")
    with database.connect() as sql:
        sql.execute("BEGIN IMMEDIATE")
        row = sql.execute(
            "SELECT expected_thermal_frames FROM offline_processing_runs "
            "WHERE project_id=? AND run_id=? AND status='running'",
            (project_id, run_id),
        ).fetchone()
        if row is None:
            raise ValueError("active processing run not found for this project")
        if processed_thermal_frames + failed_thermal_frames > row[0]:
            raise ValueError("processing counts exceed the saved input inventory")
        updated = sql.execute(
            "UPDATE offline_processing_runs "
            "SET status=?,processed_thermal_frames=?,failed_thermal_frames=?,"
            "finished_at=CURRENT_TIMESTAMP "
            "WHERE project_id=? AND run_id=? AND status='running'",
            (outcome, processed_thermal_frames, failed_thermal_frames,
             project_id, run_id),
        )
        if updated.rowcount != 1:
            raise ValueError("stale processing run state")
