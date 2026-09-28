from __future__ import annotations

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import sqlite3

import pytest

from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
from mcm_solarcheck.services.compute_jobs import (
    ComputeCapacity,
    ComputeJob,
    ComputeJobLease,
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



def test_sqlite_claim_owner_can_release_for_another_worker(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, claims=store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)

    service.claim(running.job_id, worker_id="worker-a")
    released = service.release_claim(running.job_id, worker_id="worker-a")
    reclaimed = service.claim(running.job_id, worker_id="worker-b")

    assert released == running
    assert reclaimed == running
    assert store.get(running.job_id) == running


def test_sqlite_non_owner_worker_cannot_release_claim(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, claims=store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    service.claim(running.job_id, worker_id="worker-a")

    with pytest.raises(PermissionError, match="claim mismatch"):
        service.release_claim(running.job_id, worker_id="worker-b")

    with pytest.raises(RuntimeError, match="another worker"):
        service.claim(running.job_id, worker_id="worker-b")

    assert store.get(running.job_id) == running


def test_compute_service_release_claim_fails_closed_without_adapter(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)

    with pytest.raises(RuntimeError, match="claim source is required"):
        service.release_claim(running.job_id, worker_id="worker-a")

    assert store.get(running.job_id) == running



def test_sqlite_expired_worker_lease_can_be_reclaimed(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, claims=store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    service.claim(
        running.job_id,
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
    )

    with pytest.raises(RuntimeError, match="another worker"):
        service.claim(
            running.job_id,
            worker_id="worker-b",
            lease=ComputeJobLease(start + timedelta(minutes=4), timedelta(minutes=5)),
        )

    reclaimed = service.claim(
        running.job_id,
        worker_id="worker-b",
        lease=ComputeJobLease(start + timedelta(minutes=5), timedelta(minutes=5)),
    )

    assert reclaimed == running


def test_sqlite_worker_can_renew_its_lease(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, claims=store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    service.claim(
        running.job_id,
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
    )
    renewed = service.claim(
        running.job_id,
        worker_id="worker-a",
        lease=ComputeJobLease(start + timedelta(minutes=4), timedelta(minutes=5)),
    )

    assert renewed == running

    with pytest.raises(RuntimeError, match="another worker"):
        service.claim(
            running.job_id,
            worker_id="worker-b",
            lease=ComputeJobLease(start + timedelta(minutes=6), timedelta(minutes=5)),
        )


def test_compute_job_lease_requires_utc_positive_duration() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ComputeJobLease(datetime(2026, 1, 1), timedelta(minutes=1))

    with pytest.raises(ValueError, match="positive"):
        ComputeJobLease(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            timedelta(0),
        )



def test_sqlite_worker_can_finish_before_lease_expiry(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, claims=store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    service.claim(
        running.job_id,
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
    )

    finished = service.finish_claimed(
        running.job_id,
        worker_id="worker-a",
        succeeded=True,
        now=start + timedelta(minutes=4, seconds=59),
    )

    assert finished.status is ComputeJobStatus.COMPLETED


def test_sqlite_worker_cannot_finish_at_or_after_lease_expiry(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, claims=store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    service.claim(
        running.job_id,
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
    )

    with pytest.raises(PermissionError, match="lease expired"):
        service.finish_claimed(
            running.job_id,
            worker_id="worker-a",
            succeeded=True,
            now=start + timedelta(minutes=5),
        )

    assert store.get(running.job_id) == running


def test_old_worker_cannot_finish_after_expired_lease_is_reclaimed(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, claims=store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    service.claim(
        running.job_id,
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
    )
    service.claim(
        running.job_id,
        worker_id="worker-b",
        lease=ComputeJobLease(start + timedelta(minutes=5), timedelta(minutes=5)),
    )

    with pytest.raises(PermissionError, match="claim mismatch"):
        service.finish_claimed(
            running.job_id,
            worker_id="worker-a",
            succeeded=True,
            now=start + timedelta(minutes=6),
        )

    finished = service.finish_claimed(
        running.job_id,
        worker_id="worker-b",
        succeeded=False,
        now=start + timedelta(minutes=6),
    )
    assert finished.status is ComputeJobStatus.FAILED



def test_sqlite_worker_can_release_before_lease_expiry(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, claims=store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    service.claim(
        running.job_id,
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
    )

    released = service.release_claim(
        running.job_id,
        worker_id="worker-a",
        now=start + timedelta(minutes=4, seconds=59),
    )
    reclaimed = service.claim(
        running.job_id,
        worker_id="worker-b",
        lease=ComputeJobLease(start + timedelta(minutes=5), timedelta(minutes=5)),
    )

    assert released == running
    assert reclaimed == running


def test_sqlite_worker_cannot_release_at_or_after_lease_expiry(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, claims=store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    service.claim(
        running.job_id,
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
    )

    with pytest.raises(PermissionError, match="lease expired"):
        service.release_claim(
            running.job_id,
            worker_id="worker-a",
            now=start + timedelta(minutes=5),
        )

    reclaimed = service.claim(
        running.job_id,
        worker_id="worker-b",
        lease=ComputeJobLease(start + timedelta(minutes=5), timedelta(minutes=5)),
    )
    assert reclaimed == running


def test_sqlite_leased_release_requires_current_time(tmp_path) -> None:
    store = SQLiteComputeJobStore(tmp_path / "compute-jobs.sqlite")
    service = ComputeJobService(store, claims=store)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    service.claim(
        running.job_id,
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
    )

    with pytest.raises(ValueError, match="current UTC time is required"):
        service.release_claim(running.job_id, worker_id="worker-a")



def test_sqlite_store_migrates_legacy_compute_jobs_without_data_loss(tmp_path) -> None:
    database = tmp_path / "compute-jobs.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE compute_jobs (
                job_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO compute_jobs (job_id, user_id, project_id, status)
            VALUES (?, ?, ?, ?)
            """,
            ("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING.value),
        )

    store = SQLiteComputeJobStore(database)
    service = ComputeJobService(store, claims=store)
    existing = store.get("job-a")
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    claimed = service.claim(
        existing.job_id,
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
    )
    finished = service.finish_claimed(
        existing.job_id,
        worker_id="worker-a",
        succeeded=True,
        now=start + timedelta(minutes=1),
    )

    assert existing == ComputeJob(
        "job-a",
        "user-a",
        "project-a",
        ComputeJobStatus.RUNNING,
    )
    assert claimed == existing
    assert finished.status is ComputeJobStatus.COMPLETED

    with sqlite3.connect(database) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(compute_jobs)")
        }
        row = connection.execute(
            """
            SELECT user_id, project_id, status, worker_id, lease_expires_at
            FROM compute_jobs
            WHERE job_id = ?
            """,
            ("job-a",),
        ).fetchone()

    assert {"worker_id", "lease_expires_at"} <= columns
    assert row == (
        "user-a",
        "project-a",
        ComputeJobStatus.COMPLETED.value,
        "worker-a",
        (start + timedelta(minutes=5)).isoformat(),
    )



def test_sqlite_concurrent_workers_exclusively_claim_one_job(tmp_path) -> None:
    database = tmp_path / "compute-jobs.sqlite"
    store = SQLiteComputeJobStore(database)
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    store.create(running)
    barrier = Barrier(2)

    def claim(worker_id: str) -> tuple[str, str]:
        worker_store = SQLiteComputeJobStore(database)
        barrier.wait()
        try:
            worker_store.claim(running.job_id, worker_id)
        except RuntimeError as exc:
            return ("rejected", str(exc))
        return ("claimed", worker_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, ("worker-a", "worker-b")))

    claimed = [result for result in results if result[0] == "claimed"]
    rejected = [result for result in results if result[0] == "rejected"]

    assert len(claimed) == 1
    assert len(rejected) == 1
    assert "already claimed by another worker" in rejected[0][1]

    winner = claimed[0][1]
    assert store.claim(running.job_id, winner) == running
