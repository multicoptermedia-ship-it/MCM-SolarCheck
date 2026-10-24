"""Fail-closed review prerequisite for the shipped offline desktop.

The current offline pipeline imports and stages *raw candidates*, but has no
worker which can prove complete geometric/radiometric image processing.
An arbitrary SQLite status='completed' is NOT proof of such a pipeline.
Never synthesize approval from frame counts, candidate rows or a GUI click.
"""
from __future__ import annotations


def verified_offline_processing_blockers(database, project_id: str) -> tuple[str, ...]:
    """Return blocking reasons until worker-verified completion is implemented.

    Preserves any historical reviews/reports on disk: an absent new processing
    attestation changes permissions only, never erases human audit records.
    """
    from mcm_solarcheck.services.offline_processing_runs import (
        latest_offline_processing_run,
    )

    run = latest_offline_processing_run(database, project_id)
    if run is None:
        return ("no verified complete offline processing run",)
    if run.stale_inputs:
        return ("processing inputs changed since the last run",)
    if run.status == "running":
        return ("offline processing run is still running",)
    if run.status == "failed":
        return ("offline processing run failed",)
    if run.status == "cancelled":
        return ("offline processing run was cancelled",)
    # IMPORTANT: there is intentionally no trusted completion-writer yet.
    # A manually inserted or old 'completed' ledger row cannot grant Review.
    return ("processing completion lacks worker-verified evidence",)
