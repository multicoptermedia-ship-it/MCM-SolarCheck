from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
from mcm_solarcheck.services.compute_jobs import (
    ComputeJob,
    ComputeJobService,
    ComputeJobStatus,
)


def test_sqlite_compute_job_store_persists_across_instances(tmp_path) -> None:
    database = tmp_path / "compute-jobs.sqlite"
    first = SQLiteComputeJobStore(database)
    job = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.QUEUED)

    first.create(job)

    reopened = SQLiteComputeJobStore(database)
    assert reopened.get("job-a") == job


def test_sqlite_compute_job_store_rejects_duplicate_job_id(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    job = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.QUEUED)
    store.create(job)

    with pytest.raises(ValueError, match="already exists"):
        store.create(job)

    assert store.get("job-a") == job


def test_sqlite_compute_job_store_replaces_authoritative_state(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store)
    created = service.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    running = service.transition(
        created.job_id,
        ComputeJobStatus.RUNNING,
        user_id="user-a",
        project_id="project-a",
    )

    reopened = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    assert reopened.get("job-a") == running


def test_sqlite_compute_job_store_rejects_replace_for_missing_job(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    missing = ComputeJob(
        "missing",
        "user-a",
        "project-a",
        ComputeJobStatus.RUNNING,
    )

    with pytest.raises(KeyError):
        store.replace(missing)
