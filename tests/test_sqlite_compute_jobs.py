from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
from mcm_solarcheck.services.compute_jobs import (
    ComputeCapacity,
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



def test_sqlite_compute_job_store_counts_only_running_jobs(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    store.create(ComputeJob("queued", "user-a", "project-a", ComputeJobStatus.QUEUED))
    store.create(ComputeJob("running-a", "user-a", "project-a", ComputeJobStatus.RUNNING))
    store.create(ComputeJob("running-b", "user-b", "project-b", ComputeJobStatus.RUNNING))
    store.create(ComputeJob("completed", "user-c", "project-c", ComputeJobStatus.COMPLETED))
    store.create(ComputeJob("failed", "user-d", "project-d", ComputeJobStatus.FAILED))

    assert store.running_jobs() == 2


def test_compute_service_uses_sqlite_load_for_capacity_admission(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, load=store)
    capacity = ComputeCapacity(max_parallel_jobs=1)

    first = service.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )
    second = service.create(
        job_id="job-b",
        user_id="user-b",
        project_id="project-b",
    )

    first_running = service.start(
        first.job_id,
        user_id="user-a",
        project_id="project-a",
        capacity=capacity,
    )
    second_queued = service.start(
        second.job_id,
        user_id="user-b",
        project_id="project-b",
        capacity=capacity,
    )

    assert first_running.status is ComputeJobStatus.RUNNING
    assert second_queued.status is ComputeJobStatus.QUEUED
    assert store.running_jobs() == 1

    service.finish(first.job_id, succeeded=True)
    second_running = service.start(
        second.job_id,
        user_id="user-b",
        project_id="project-b",
        capacity=capacity,
    )

    assert second_running.status is ComputeJobStatus.RUNNING
    assert store.running_jobs() == 1



def test_sqlite_atomic_admission_keeps_second_job_queued(tmp_path) -> None:
    database = tmp_path / "compute-jobs.sqlite"
    store = SQLiteComputeJobStore(database)
    service = ComputeJobService(store, load=store, admission=store)
    capacity = ComputeCapacity(max_parallel_jobs=1)
    first = service.create(job_id="job-a", user_id="user-a", project_id="project-a")
    second = service.create(job_id="job-b", user_id="user-b", project_id="project-b")

    first_started = service.start(
        first.job_id,
        user_id="user-a",
        project_id="project-a",
        capacity=capacity,
    )
    second_result = service.start(
        second.job_id,
        user_id="user-b",
        project_id="project-b",
        capacity=capacity,
    )

    assert first_started.status is ComputeJobStatus.RUNNING
    assert second_result.status is ComputeJobStatus.QUEUED
    assert store.running_jobs() == 1


def test_sqlite_atomic_admission_rejects_stale_job_snapshot(tmp_path) -> None:
    database = tmp_path / "compute-jobs.sqlite"
    store = SQLiteComputeJobStore(database)
    queued = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.QUEUED)
    store.create(queued)
    store.replace(
        ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    )

    with pytest.raises(ValueError, match="changed before admission"):
        store.try_start(queued, ComputeCapacity(max_parallel_jobs=2))

    assert store.running_jobs() == 1



def test_sqlite_worker_claim_is_exclusive_and_idempotent(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)

    assert store.claim("job-a", "worker-a") == running
    assert store.claim("job-a", "worker-a") == running

    with pytest.raises(RuntimeError, match="another worker"):
        store.claim("job-a", "worker-b")

    assert store.get("job-a") == running


@pytest.mark.parametrize(
    "status",
    (ComputeJobStatus.QUEUED, ComputeJobStatus.COMPLETED, ComputeJobStatus.FAILED),
)
def test_sqlite_worker_claim_requires_running_job(
    tmp_path,
    status: ComputeJobStatus,
) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    job = ComputeJob("job-a", "user-a", "project-a", status)
    store.create(job)

    with pytest.raises(ValueError, match="only a running compute job"):
        store.claim(job.job_id, "worker-a")

    assert store.get(job.job_id) == job


def test_sqlite_worker_claim_requires_worker_identity(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    store.create(
        ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    )

    with pytest.raises(ValueError, match="worker_id"):
        store.claim("job-a", " ")



@pytest.mark.parametrize(
    ("succeeded", "expected"),
    (
        (True, ComputeJobStatus.COMPLETED),
        (False, ComputeJobStatus.FAILED),
    ),
)
def test_sqlite_claim_owner_can_finish_job(
    tmp_path,
    succeeded: bool,
    expected: ComputeJobStatus,
) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    store.claim(running.job_id, "worker-a")

    finished = store.finish_claimed(
        running.job_id,
        "worker-a",
        succeeded=succeeded,
    )

    assert finished.status is expected
    assert store.get(running.job_id) == finished


def test_sqlite_non_owner_worker_cannot_finish_claimed_job(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    store.claim(running.job_id, "worker-a")

    with pytest.raises(PermissionError, match="claim mismatch"):
        store.finish_claimed(running.job_id, "worker-b", succeeded=True)

    assert store.get(running.job_id) == running


def test_sqlite_unclaimed_job_cannot_be_finished_by_worker(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)

    with pytest.raises(PermissionError, match="claim mismatch"):
        store.finish_claimed(running.job_id, "worker-a", succeeded=True)

    assert store.get(running.job_id) == running



def test_compute_service_routes_worker_claim_lifecycle_through_adapter(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(
        store,
        load=store,
        admission=store,
        claims=store,
    )
    capacity = ComputeCapacity(max_parallel_jobs=1)
    created = service.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )
    running = service.start(
        created.job_id,
        user_id="user-a",
        project_id="project-a",
        capacity=capacity,
    )

    claimed = service.claim(running.job_id, worker_id="worker-a")
    finished = service.finish_claimed(
        claimed.job_id,
        worker_id="worker-a",
        succeeded=True,
    )

    assert claimed == running
    assert finished.status is ComputeJobStatus.COMPLETED
    assert store.get(created.job_id) == finished


def test_compute_service_fails_closed_without_worker_claim_adapter(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)

    with pytest.raises(RuntimeError, match="claim source is required"):
        service.claim(running.job_id, worker_id="worker-a")

    with pytest.raises(RuntimeError, match="claim source is required"):
        service.finish_claimed(
            running.job_id,
            worker_id="worker-a",
            succeeded=True,
        )

    assert store.get(running.job_id) == running
