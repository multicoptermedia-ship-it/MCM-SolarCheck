from __future__ import annotations

import pytest

from mcm_solarcheck.services.compute_jobs import (
    ComputeCapacity,
    ComputeJob,
    ComputeJobStatus,
    transition_job,
)


def test_compute_job_preserves_tenant_and_project_identity() -> None:
    job = ComputeJob(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
        status=ComputeJobStatus.QUEUED,
    )

    assert job.job_id == "job-a"
    assert job.user_id == "user-a"
    assert job.project_id == "project-a"
    assert job.status is ComputeJobStatus.QUEUED


@pytest.mark.parametrize("field", ("job_id", "user_id", "project_id"))
@pytest.mark.parametrize("value", ("", "   ", None))
def test_compute_job_rejects_missing_identity(field, value) -> None:
    values = {
        "job_id": "job-a",
        "user_id": "user-a",
        "project_id": "project-a",
        "status": ComputeJobStatus.QUEUED,
    }
    values[field] = value

    with pytest.raises(ValueError, match=field):
        ComputeJob(**values)


def test_compute_job_rejects_untyped_status_fail_closed() -> None:
    with pytest.raises(ValueError, match="ComputeJobStatus"):
        ComputeJob(
            job_id="job-a",
            user_id="user-a",
            project_id="project-a",
            status="queued",
        )


def test_distinct_users_can_hold_distinct_queued_jobs() -> None:
    first = ComputeJob(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
        status=ComputeJobStatus.QUEUED,
    )
    second = ComputeJob(
        job_id="job-b",
        user_id="user-b",
        project_id="project-b",
        status=ComputeJobStatus.QUEUED,
    )

    assert first.job_id != second.job_id
    assert first.user_id != second.user_id
    assert first.project_id != second.project_id


def test_compute_capacity_starts_jobs_only_while_slots_are_free() -> None:
    capacity = ComputeCapacity(max_parallel_jobs=2)

    assert capacity.admission_status(0) is ComputeJobStatus.RUNNING
    assert capacity.admission_status(1) is ComputeJobStatus.RUNNING
    assert capacity.admission_status(2) is ComputeJobStatus.QUEUED
    assert capacity.admission_status(3) is ComputeJobStatus.QUEUED


@pytest.mark.parametrize("value", (0, -1, 1.5, True))
def test_compute_capacity_rejects_invalid_parallel_limit(value) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        ComputeCapacity(max_parallel_jobs=value)


@pytest.mark.parametrize("running_jobs", (-1, 1.5, True))
def test_compute_capacity_rejects_invalid_running_job_count(running_jobs) -> None:
    capacity = ComputeCapacity(max_parallel_jobs=2)

    with pytest.raises(ValueError, match="non-negative integer"):
        capacity.admission_status(running_jobs)


def test_single_worker_serializes_two_tenant_jobs_without_identity_leakage() -> None:
    capacity = ComputeCapacity(max_parallel_jobs=1)
    first = ComputeJob(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
        status=capacity.admission_status(0),
    )
    second = ComputeJob(
        job_id="job-b",
        user_id="user-b",
        project_id="project-b",
        status=capacity.admission_status(1),
    )

    assert first.status is ComputeJobStatus.RUNNING
    assert second.status is ComputeJobStatus.QUEUED
    assert (first.user_id, first.project_id) == ("user-a", "project-a")
    assert (second.user_id, second.project_id) == ("user-b", "project-b")


@pytest.mark.parametrize(
    ("source", "target"),
    (
        (ComputeJobStatus.QUEUED, ComputeJobStatus.RUNNING),
        (ComputeJobStatus.QUEUED, ComputeJobStatus.FAILED),
        (ComputeJobStatus.RUNNING, ComputeJobStatus.COMPLETED),
        (ComputeJobStatus.RUNNING, ComputeJobStatus.FAILED),
    ),
)
def test_compute_job_allows_only_declared_forward_transitions(source, target) -> None:
    job = ComputeJob("job-a", "user-a", "project-a", source)

    transitioned = transition_job(job, target)

    assert transitioned.status is target
    assert transitioned.job_id == job.job_id
    assert transitioned.user_id == job.user_id
    assert transitioned.project_id == job.project_id


@pytest.mark.parametrize(
    ("source", "target"),
    (
        (ComputeJobStatus.QUEUED, ComputeJobStatus.COMPLETED),
        (ComputeJobStatus.RUNNING, ComputeJobStatus.QUEUED),
        (ComputeJobStatus.COMPLETED, ComputeJobStatus.RUNNING),
        (ComputeJobStatus.FAILED, ComputeJobStatus.QUEUED),
        (ComputeJobStatus.COMPLETED, ComputeJobStatus.COMPLETED),
    ),
)
def test_compute_job_rejects_invalid_or_replayed_transitions(source, target) -> None:
    job = ComputeJob("job-a", "user-a", "project-a", source)

    with pytest.raises(ValueError, match="invalid compute job transition"):
        transition_job(job, target)


def test_compute_job_transition_rejects_untyped_target_status() -> None:
    job = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.QUEUED)

    with pytest.raises(ValueError, match="ComputeJobStatus"):
        transition_job(job, "running")



class _InMemoryComputeJobStore:
    def __init__(self) -> None:
        self.jobs: dict[str, ComputeJob] = {}

    def create(self, job: ComputeJob) -> None:
        if job.job_id in self.jobs:
            raise ValueError("compute job already exists")
        self.jobs[job.job_id] = job

    def get(self, job_id: str) -> ComputeJob:
        return self.jobs[job_id]

    def replace(self, job: ComputeJob) -> None:
        if job.job_id not in self.jobs:
            raise KeyError(job.job_id)
        self.jobs[job.job_id] = job


def test_compute_job_service_owns_persistence_and_transition_boundary() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    service = ComputeJobService(store)

    created = service.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )
    running = service.transition(created.job_id, ComputeJobStatus.RUNNING, user_id="user-a", project_id="project-a")
    completed = service.transition(running.job_id, ComputeJobStatus.COMPLETED, user_id="user-a", project_id="project-a")

    assert store.get("job-a") == completed
    assert completed.status is ComputeJobStatus.COMPLETED
    assert (completed.user_id, completed.project_id) == ("user-a", "project-a")


def test_compute_job_service_rejects_invalid_transition_without_persisting() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    service = ComputeJobService(store)
    created = service.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    with pytest.raises(ValueError, match="invalid compute job transition"):
        service.transition(created.job_id, ComputeJobStatus.COMPLETED, user_id="user-a", project_id="project-a")

    assert store.get("job-a") == created



@pytest.mark.parametrize(
    ("user_id", "project_id"),
    (
        ("user-b", "project-a"),
        ("user-a", "project-b"),
        ("user-b", "project-b"),
    ),
)
def test_compute_job_service_denies_cross_tenant_or_project_reads(
    user_id: str,
    project_id: str,
) -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    service = ComputeJobService(store)
    service.create(job_id="job-a", user_id="user-a", project_id="project-a")

    with pytest.raises(PermissionError, match="access denied"):
        service.get("job-a", user_id=user_id, project_id=project_id)


def test_compute_job_service_denies_cross_tenant_transition_without_persisting() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    service = ComputeJobService(store)
    created = service.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    with pytest.raises(PermissionError, match="access denied"):
        service.transition(
            "job-a",
            ComputeJobStatus.RUNNING,
            user_id="user-b",
            project_id="project-a",
        )

    assert store.get("job-a") == created



def test_compute_job_service_starts_job_when_capacity_is_available() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    service = ComputeJobService(store)
    service.create(job_id="job-a", user_id="user-a", project_id="project-a")

    started = service.start(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        capacity=ComputeCapacity(max_parallel_jobs=2),
        running_jobs=1,
    )

    assert started.status is ComputeJobStatus.RUNNING
    assert store.get("job-a") == started


def test_compute_job_service_keeps_job_queued_when_capacity_is_full() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    service = ComputeJobService(store)
    queued = service.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    admitted = service.start(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        capacity=ComputeCapacity(max_parallel_jobs=1),
        running_jobs=1,
    )

    assert admitted == queued
    assert store.get("job-a") == queued


def test_compute_job_service_checks_ownership_before_capacity_admission() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    service = ComputeJobService(store)
    queued = service.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    with pytest.raises(PermissionError, match="access denied"):
        service.start(
            "job-a",
            user_id="user-b",
            project_id="project-a",
            capacity=ComputeCapacity(max_parallel_jobs=2),
            running_jobs=0,
        )

    assert store.get("job-a") == queued



class _StaticComputeJobLoad:
    def __init__(self, running_jobs: int) -> None:
        self._running_jobs = running_jobs

    def running_jobs(self) -> int:
        return self._running_jobs


def test_compute_job_service_sources_admission_load_server_side() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    service = ComputeJobService(store, load=_StaticComputeJobLoad(1))
    service.create(job_id="job-a", user_id="user-a", project_id="project-a")

    started = service.start(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        capacity=ComputeCapacity(max_parallel_jobs=2),
    )

    assert started.status is ComputeJobStatus.RUNNING
    assert store.get("job-a") == started


def test_compute_job_service_server_load_keeps_excess_work_queued() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    service = ComputeJobService(store, load=_StaticComputeJobLoad(2))
    queued = service.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    admitted = service.start(
        "job-a",
        user_id="user-a",
        project_id="project-a",
        capacity=ComputeCapacity(max_parallel_jobs=2),
    )

    assert admitted == queued
    assert store.get("job-a") == queued


def test_compute_job_service_fails_closed_without_admission_load_source() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    service = ComputeJobService(store)
    queued = service.create(
        job_id="job-a",
        user_id="user-a",
        project_id="project-a",
    )

    with pytest.raises(RuntimeError, match="load source is required"):
        service.start(
            "job-a",
            user_id="user-a",
            project_id="project-a",
            capacity=ComputeCapacity(max_parallel_jobs=1),
        )

    assert store.get("job-a") == queued



@pytest.mark.parametrize(
    ("succeeded", "expected"),
    (
        (True, ComputeJobStatus.COMPLETED),
        (False, ComputeJobStatus.FAILED),
    ),
)
def test_compute_job_service_finishes_running_worker_job(
    succeeded: bool,
    expected: ComputeJobStatus,
) -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
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

    finished = service.finish(running.job_id, succeeded=succeeded)

    assert finished.status is expected
    assert finished.job_id == running.job_id
    assert finished.user_id == running.user_id
    assert finished.project_id == running.project_id
    assert store.get("job-a") == finished


@pytest.mark.parametrize(
    "status",
    (ComputeJobStatus.QUEUED, ComputeJobStatus.COMPLETED, ComputeJobStatus.FAILED),
)
def test_compute_job_service_rejects_worker_finish_outside_running_state(
    status: ComputeJobStatus,
) -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    job = ComputeJob("job-a", "user-a", "project-a", status)
    store.create(job)
    service = ComputeJobService(store)

    with pytest.raises(ValueError, match="only a running compute job"):
        service.finish("job-a", succeeded=True)

    assert store.get("job-a") == job



def test_compute_job_service_end_to_end_lifecycle_isolated_and_capacity_bounded() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    load = _StaticComputeJobLoad(0)
    service = ComputeJobService(store, load=load)
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
    assert first_running.status is ComputeJobStatus.RUNNING

    load._running_jobs = 1
    second_queued = service.start(
        second.job_id,
        user_id="user-b",
        project_id="project-b",
        capacity=capacity,
    )
    assert second_queued.status is ComputeJobStatus.QUEUED

    with pytest.raises(PermissionError, match="access denied"):
        service.get(
            first.job_id,
            user_id="user-b",
            project_id="project-b",
        )

    first_done = service.finish(first.job_id, succeeded=True)
    assert first_done.status is ComputeJobStatus.COMPLETED
    assert (first_done.user_id, first_done.project_id) == ("user-a", "project-a")

    load._running_jobs = 0
    second_running = service.start(
        second.job_id,
        user_id="user-b",
        project_id="project-b",
        capacity=capacity,
    )
    second_failed = service.finish(second_running.job_id, succeeded=False)

    assert second_failed.status is ComputeJobStatus.FAILED
    assert (second_failed.user_id, second_failed.project_id) == ("user-b", "project-b")
    assert store.get(first.job_id) == first_done
    assert store.get(second.job_id) == second_failed



class _RejectingComputeJobClaims:
    def claim(self, job_id: str, worker_id: str, lease=None) -> ComputeJob:
        raise AssertionError("claim should not be called")

    def release_claim(self, job_id: str, worker_id: str, *, now=None) -> ComputeJob:
        raise AssertionError("release should not be called")

    def finish_claimed(
        self,
        job_id: str,
        worker_id: str,
        *,
        succeeded: bool,
        now=None,
    ) -> ComputeJob:
        raise AssertionError("finish_claimed should not be called")


def test_compute_job_service_blocks_legacy_finish_when_claims_enabled() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService

    store = _InMemoryComputeJobStore()
    running = ComputeJob(
        "job-a",
        "user-a",
        "project-a",
        ComputeJobStatus.RUNNING,
    )
    store.create(running)
    service = ComputeJobService(store, claims=_RejectingComputeJobClaims())

    with pytest.raises(RuntimeError, match="finish_claimed"):
        service.finish(running.job_id, succeeded=True)

    assert store.get(running.job_id) == running


def test_compute_job_service_claim_rejects_queued_job() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService
    class Claims:
        def claim(self, *args, **kwargs): raise AssertionError("claim must not be called")
    store = _InMemoryComputeJobStore()
    store.create(ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.QUEUED))
    service = ComputeJobService(store, claims=Claims())
    with pytest.raises(ValueError, match="running compute job"):
        service.claim("job-a", worker_id="worker-a")


def test_compute_job_service_claim_rejects_completed_job() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService
    class Claims:
        def claim(self, *args, **kwargs): raise AssertionError("claim must not be called")
    store = _InMemoryComputeJobStore()
    store.create(ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.COMPLETED))
    service = ComputeJobService(store, claims=Claims())
    with pytest.raises(ValueError, match="running compute job"):
        service.claim("job-a", worker_id="worker-a")


def test_compute_job_service_claim_rejects_failed_job() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService
    class Claims:
        def claim(self, *args, **kwargs): raise AssertionError("claim must not be called")
    store = _InMemoryComputeJobStore()
    store.create(ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.FAILED))
    service = ComputeJobService(store, claims=Claims())
    with pytest.raises(ValueError, match="running compute job"):
        service.claim("job-a", worker_id="worker-a")


def test_compute_job_service_claim_accepts_running_job() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJobService
    running = ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.RUNNING)
    class Claims:
        def __init__(self): self.calls = []
        def claim(self, job_id, worker_id, lease=None):
            self.calls.append((job_id, worker_id, lease))
            return running
    store = _InMemoryComputeJobStore(); store.create(running); claims = Claims()
    service = ComputeJobService(store, claims=claims)
    assert service.claim("job-a", worker_id="worker-a") == running
    assert claims.calls == [("job-a", "worker-a", None)]


def test_compute_job_service_renew_claim_rejects_queued_job() -> None:
    from datetime import datetime, timedelta, timezone
    from mcm_solarcheck.services.compute_jobs import ComputeJobLease, ComputeJobService
    lease = ComputeJobLease(datetime(2026, 1, 1, tzinfo=timezone.utc), timedelta(minutes=5))
    class Claims:
        def renew_claim(self, *args, **kwargs): raise AssertionError("renew must not be called")
    store = _InMemoryComputeJobStore(); store.create(ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.QUEUED))
    with pytest.raises(ValueError, match="running compute job"):
        ComputeJobService(store, claims=Claims()).renew_claim("job-a", worker_id="worker-a", lease=lease)


def test_compute_job_service_renew_claim_rejects_completed_job() -> None:
    from datetime import datetime, timedelta, timezone
    from mcm_solarcheck.services.compute_jobs import ComputeJobLease, ComputeJobService
    lease = ComputeJobLease(datetime(2026, 1, 1, tzinfo=timezone.utc), timedelta(minutes=5))
    class Claims:
        def renew_claim(self, *args, **kwargs): raise AssertionError("renew must not be called")
    store = _InMemoryComputeJobStore(); store.create(ComputeJob("job-a", "user-a", "project-a", ComputeJobStatus.COMPLETED))
    with pytest.raises(ValueError, match="running compute job"):
        ComputeJobService(store, claims=Claims()).renew_claim("job-a", worker_id="worker-a", lease=lease)
