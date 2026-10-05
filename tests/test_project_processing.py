from pathlib import Path
from types import SimpleNamespace

import pytest

from mcm_solarcheck.services.project_processing import (
    ProjectProcessingRequest,
    ProjectProcessingService,
    ProjectProcessingState,
    ComputeJobProcessingStateRecorder,
    ProjectProcessingConflict,
)


def import_result(*, imported=2, paired=1, failures=0):
    return SimpleNamespace(
        thermal_batch=SimpleNamespace(
            results=tuple(object() for _ in range(imported)),
            failures=tuple(object() for _ in range(failures)),
        ),
        pairs=tuple(object() for _ in range(paired)),
    )


def test_processing_resolves_customer_project_uploads_and_records_lifecycle(tmp_path) -> None:
    states = []
    imported_directories = []
    service = ProjectProcessingService(
        lambda customer_id, project_id: (customer_id, project_id) == ("user-1", "P-1"),
        lambda customer_id, project_id: tmp_path,
        lambda directory: imported_directories.append(directory) or import_result(),
        lambda customer_id, project_id, state: states.append((customer_id, project_id, state)),
    )

    result = service.process(ProjectProcessingRequest("user-1", "P-1"))

    assert imported_directories == [tmp_path]
    assert states == [
        ("user-1", "P-1", ProjectProcessingState.RUNNING),
        ("user-1", "P-1", ProjectProcessingState.COMPLETED),
    ]
    assert result.state is ProjectProcessingState.COMPLETED
    assert result.imported_thermal_frames == 2
    assert result.paired_frames == 1
    assert result.import_failures == 0


def test_processing_rejects_foreign_project_before_resolving_uploads() -> None:
    resolved = []
    states = []
    service = ProjectProcessingService(
        lambda customer_id, project_id: False,
        lambda customer_id, project_id: resolved.append(True) or Path("/should-not-resolve"),
        lambda directory: import_result(),
        lambda customer_id, project_id, state: states.append(state),
    )

    with pytest.raises(PermissionError):
        service.process(ProjectProcessingRequest("user-1", "P-other"))

    assert resolved == []
    assert states == []


def test_processing_records_failed_state_when_import_raises(tmp_path) -> None:
    states = []

    def fail_import(directory):
        raise RuntimeError("import failed")

    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        fail_import,
        lambda customer_id, project_id, state: states.append(state),
    )

    with pytest.raises(RuntimeError):
        service.process(ProjectProcessingRequest("user-1", "P-1"))

    assert states == [
        ProjectProcessingState.RUNNING,
        ProjectProcessingState.FAILED,
    ]


@pytest.mark.parametrize(
    ("customer_id", "project_id"),
    [("", "P-1"), ("user-1", " "), (" ", "")],
)
def test_processing_rejects_invalid_identity_before_dependencies(customer_id, project_id) -> None:
    called = []
    service = ProjectProcessingService(
        lambda customer, project: called.append("ownership") or True,
        lambda customer, project: called.append("directory") or Path("."),
        lambda directory: called.append("import") or import_result(),
        lambda customer, project, state: called.append("state"),
    )

    with pytest.raises(ValueError):
        service.process(ProjectProcessingRequest(customer_id, project_id))

    assert called == []


def test_processing_rejects_missing_upload_directory_before_state_change(tmp_path) -> None:
    states = []
    imported = []
    missing = tmp_path / "missing"
    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: missing,
        lambda directory: imported.append(directory) or import_result(),
        lambda customer_id, project_id, state: states.append(state),
    )

    with pytest.raises(ValueError):
        service.process(ProjectProcessingRequest("user-1", "P-1"))

    assert imported == []
    assert states == []


def test_processing_persists_import_before_completed_state(tmp_path) -> None:
    events = []
    imported = import_result(imported=3, paired=2)
    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: events.append(("import", directory)) or imported,
        lambda customer_id, project_id, state: events.append(("state", state)),
        lambda customer_id, project_id, result: events.append(
            ("persist", customer_id, project_id, result)
        ),
    )

    result = service.process(ProjectProcessingRequest("user-1", "P-1"))

    assert events == [
        ("state", ProjectProcessingState.RUNNING),
        ("import", tmp_path),
        ("persist", "user-1", "P-1", imported),
        ("state", ProjectProcessingState.COMPLETED),
    ]
    assert result.state is ProjectProcessingState.COMPLETED


def test_processing_records_failed_state_when_persistence_raises(tmp_path) -> None:
    states = []

    def fail_persistence(customer_id, project_id, imported):
        raise RuntimeError("persistence failed")

    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: import_result(),
        lambda customer_id, project_id, state: states.append(state),
        fail_persistence,
    )

    with pytest.raises(RuntimeError, match="persistence failed"):
        service.process(ProjectProcessingRequest("user-1", "P-1"))

    assert states == [
        ProjectProcessingState.RUNNING,
        ProjectProcessingState.FAILED,
    ]


def test_compute_job_processing_recorder_requires_matching_running_job() -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus

    class Jobs:
        def __init__(self):
            self.job = ComputeJob("job-1", "user-1", "P-1", ComputeJobStatus.RUNNING)
            self.transitions = []

        def get(self, job_id, *, user_id, project_id):
            assert (job_id, user_id, project_id) == ("job-1", "user-1", "P-1")
            return self.job

        def transition(self, job_id, status, *, user_id, project_id):
            self.transitions.append((job_id, status, user_id, project_id))

    jobs = Jobs()
    recorder = ComputeJobProcessingStateRecorder(
        jobs, job_id="job-1", customer_id="user-1", project_id="P-1"
    )
    recorder("user-1", "P-1", ProjectProcessingState.RUNNING)
    recorder("user-1", "P-1", ProjectProcessingState.COMPLETED)
    assert jobs.transitions == [
        ("job-1", ComputeJobStatus.COMPLETED, "user-1", "P-1")
    ]


def test_compute_job_processing_recorder_rejects_identity_mismatch() -> None:
    recorder = ComputeJobProcessingStateRecorder(
        object(), job_id="job-1", customer_id="user-1", project_id="P-1"
    )
    with pytest.raises(PermissionError, match="identity mismatch"):
        recorder("user-other", "P-1", ProjectProcessingState.RUNNING)


def test_compute_job_processing_recorder_hides_missing_job() -> None:
    class Jobs:
        def get(self, job_id, *, user_id, project_id):
            raise KeyError(job_id)

    recorder = ComputeJobProcessingStateRecorder(
        Jobs(), job_id="missing-job", customer_id="user-1", project_id="P-1"
    )

    with pytest.raises(PermissionError, match="not available"):
        recorder("user-1", "P-1", ProjectProcessingState.RUNNING)


def test_processing_import_failure_transitions_bound_compute_job_to_failed(tmp_path) -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus

    class Jobs:
        def __init__(self):
            self.job = ComputeJob("job-1", "user-1", "P-1", ComputeJobStatus.RUNNING)

        def get(self, job_id, *, user_id, project_id):
            assert (job_id, user_id, project_id) == ("job-1", "user-1", "P-1")
            return self.job

        def transition(self, job_id, status, *, user_id, project_id):
            assert (job_id, user_id, project_id) == ("job-1", "user-1", "P-1")
            self.job = ComputeJob(job_id, user_id, project_id, status)

    jobs = Jobs()
    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: (_ for _ in ()).throw(RuntimeError("import failed")),
        lambda customer_id, project_id, state: None,
        record_state_for_request=lambda request: ComputeJobProcessingStateRecorder(
            jobs,
            job_id=request.job_id or "",
            customer_id=request.customer_id,
            project_id=request.project_id,
        ),
    )

    with pytest.raises(RuntimeError, match="import failed"):
        service.process(ProjectProcessingRequest("user-1", "P-1", "job-1"))

    assert jobs.job.status is ComputeJobStatus.FAILED


@pytest.mark.parametrize(
    "status",
    (
        __import__("mcm_solarcheck.services.compute_jobs", fromlist=["ComputeJobStatus"]).ComputeJobStatus.QUEUED,
        __import__("mcm_solarcheck.services.compute_jobs", fromlist=["ComputeJobStatus"]).ComputeJobStatus.COMPLETED,
        __import__("mcm_solarcheck.services.compute_jobs", fromlist=["ComputeJobStatus"]).ComputeJobStatus.FAILED,
    ),
)
def test_compute_job_processing_recorder_rejects_non_running_job(status) -> None:
    from mcm_solarcheck.services.compute_jobs import ComputeJob

    class Jobs:
        def __init__(self):
            self.transitions = []

        def get(self, job_id, *, user_id, project_id):
            return ComputeJob(job_id, user_id, project_id, status)

        def transition(self, job_id, next_status, *, user_id, project_id):
            self.transitions.append((job_id, next_status, user_id, project_id))

    jobs = Jobs()
    recorder = ComputeJobProcessingStateRecorder(
        jobs, job_id="job-1", customer_id="user-1", project_id="P-1"
    )

    with pytest.raises(ValueError, match="must be running"):
        recorder("user-1", "P-1", ProjectProcessingState.RUNNING)

    assert jobs.transitions == []


def test_processing_does_not_report_success_when_completed_state_recording_fails(tmp_path) -> None:
    events = []

    def record_state(customer_id, project_id, state):
        events.append(state)
        if state is ProjectProcessingState.COMPLETED:
            raise RuntimeError("completion transition failed")

    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: import_result(),
        record_state,
        lambda customer_id, project_id, imported: events.append("persisted"),
    )

    with pytest.raises(RuntimeError, match="completion transition failed"):
        service.process(ProjectProcessingRequest("user-1", "P-1"))

    assert events == [
        ProjectProcessingState.RUNNING,
        "persisted",
        ProjectProcessingState.COMPLETED,
    ]


def test_processing_preserves_import_error_when_failed_state_recording_fails(tmp_path) -> None:
    def fail_import(directory):
        raise RuntimeError("import failed")

    def fail_failed_state(customer_id, project_id, state):
        if state is ProjectProcessingState.FAILED:
            raise OSError("failed transition unavailable")

    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        fail_import,
        fail_failed_state,
    )

    with pytest.raises(RuntimeError, match="import failed") as error:
        service.process(ProjectProcessingRequest("user-1", "P-1"))

    assert isinstance(error.value.__cause__, OSError)
    assert str(error.value.__cause__) == "failed transition unavailable"



def test_processing_recorder_passes_explicit_lease_to_claim() -> None:
    from datetime import datetime, timedelta, timezone

    from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobLease, ComputeJobStatus

    lease = ComputeJobLease(
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration=timedelta(minutes=5),
    )

    class Jobs:
        def __init__(self):
            self.claims = []

        def get(self, job_id, *, user_id, project_id):
            return ComputeJob(job_id, user_id, project_id, ComputeJobStatus.RUNNING)

        def claim(self, job_id, worker_id, lease=None):
            self.claims.append((job_id, worker_id, lease))

    jobs = Jobs()
    recorder = ComputeJobProcessingStateRecorder(
        jobs,
        job_id="job-1",
        customer_id="user-1",
        project_id="P-1",
        worker_id="worker-a",
        lease=lease,
    )

    recorder("user-1", "P-1", ProjectProcessingState.RUNNING)

    assert jobs.claims == [("job-1", "worker-a", lease)]

def test_processing_recorder_finishes_leased_claim_before_expiry(tmp_path) -> None:
    from datetime import datetime, timedelta, timezone

    from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
    from mcm_solarcheck.services.compute_jobs import (
        ComputeCapacity,
        ComputeJobLease,
        ComputeJobService,
        ComputeJobStatus,
    )

    store = SQLiteComputeJobStore(tmp_path / "jobs.sqlite")
    jobs = ComputeJobService(store, load=store, admission=store, claims=store)
    jobs.create(job_id="job-1", user_id="user-1", project_id="P-1")
    jobs.start(
        "job-1",
        user_id="user-1",
        project_id="P-1",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    recorder = ComputeJobProcessingStateRecorder(
        jobs,
        job_id="job-1",
        customer_id="user-1",
        project_id="P-1",
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
        now=lambda: start + timedelta(minutes=4),
    )

    recorder("user-1", "P-1", ProjectProcessingState.RUNNING)
    recorder("user-1", "P-1", ProjectProcessingState.COMPLETED)

    assert jobs.get(
        "job-1", user_id="user-1", project_id="P-1"
    ).status is ComputeJobStatus.COMPLETED


def test_processing_recorder_rejects_second_worker_for_claimed_job(tmp_path) -> None:
    from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
    from mcm_solarcheck.services.compute_jobs import (
        ComputeCapacity,
        ComputeJobService,
    )

    store = SQLiteComputeJobStore(tmp_path / "jobs.sqlite")
    jobs = ComputeJobService(store, load=store, admission=store, claims=store)
    jobs.create(job_id="job-1", user_id="user-1", project_id="P-1")
    jobs.start(
        "job-1",
        user_id="user-1",
        project_id="P-1",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    first = ComputeJobProcessingStateRecorder(
        jobs,
        job_id="job-1",
        customer_id="user-1",
        project_id="P-1",
        worker_id="worker-a",
    )
    second = ComputeJobProcessingStateRecorder(
        jobs,
        job_id="job-1",
        customer_id="user-1",
        project_id="P-1",
        worker_id="worker-b",
    )

    first("user-1", "P-1", ProjectProcessingState.RUNNING)

    with pytest.raises(ProjectProcessingConflict, match="already running"):
        second("user-1", "P-1", ProjectProcessingState.RUNNING)


def test_claimed_processing_import_failure_finishes_job_failed(tmp_path) -> None:
    from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
    from mcm_solarcheck.services.compute_jobs import (
        ComputeCapacity,
        ComputeJobService,
        ComputeJobStatus,
    )

    store = SQLiteComputeJobStore(tmp_path / "jobs.sqlite")
    jobs = ComputeJobService(store, load=store, admission=store, claims=store)
    jobs.create(job_id="job-1", user_id="user-1", project_id="P-1")
    jobs.start(
        "job-1",
        user_id="user-1",
        project_id="P-1",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: (_ for _ in ()).throw(RuntimeError("import failed")),
        record_state_for_request=lambda request: ComputeJobProcessingStateRecorder(
            jobs,
            job_id=request.job_id or "",
            customer_id=request.customer_id,
            project_id=request.project_id,
            worker_id="worker-a",
        ),
    )

    with pytest.raises(RuntimeError, match="import failed"):
        service.process(ProjectProcessingRequest("user-1", "P-1", "job-1"))

    assert store.get("job-1").status is ComputeJobStatus.FAILED


def test_claimed_processing_success_finishes_job_completed(tmp_path) -> None:
    from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
    from mcm_solarcheck.services.compute_jobs import (
        ComputeCapacity,
        ComputeJobService,
        ComputeJobStatus,
    )

    store = SQLiteComputeJobStore(tmp_path / "jobs.sqlite")
    jobs = ComputeJobService(store, load=store, admission=store, claims=store)
    jobs.create(job_id="job-1", user_id="user-1", project_id="P-1")
    jobs.start(
        "job-1",
        user_id="user-1",
        project_id="P-1",
        capacity=ComputeCapacity(max_parallel_jobs=1),
    )
    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: import_result(imported=1, paired=1),
        record_state_for_request=lambda request: ComputeJobProcessingStateRecorder(
            jobs,
            job_id=request.job_id or "",
            customer_id=request.customer_id,
            project_id=request.project_id,
            worker_id="worker-a",
        ),
    )

    result = service.process(ProjectProcessingRequest("user-1", "P-1", "job-1"))

    assert result.state is ProjectProcessingState.COMPLETED
    assert store.get("job-1").status is ComputeJobStatus.COMPLETED


def test_processing_recorder_heartbeat_renews_active_lease(tmp_path) -> None:
    from datetime import datetime, timedelta, timezone

    from mcm_solarcheck.infrastructure.sqlite_compute_jobs import SQLiteComputeJobStore
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity, ComputeJobLease, ComputeJobService

    store = SQLiteComputeJobStore(tmp_path / "jobs.sqlite")
    jobs = ComputeJobService(store, load=store, admission=store, claims=store)
    jobs.create(job_id="job-1", user_id="user-1", project_id="P-1")
    jobs.start("job-1", user_id="user-1", project_id="P-1", capacity=ComputeCapacity(max_parallel_jobs=1))
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    renewed = ComputeJobLease(start + timedelta(minutes=4), timedelta(minutes=5))
    recorder = ComputeJobProcessingStateRecorder(
        jobs,
        job_id="job-1",
        customer_id="user-1",
        project_id="P-1",
        worker_id="worker-a",
        lease=ComputeJobLease(start, timedelta(minutes=5)),
        renew_lease=lambda: renewed,
    )

    recorder("user-1", "P-1", ProjectProcessingState.RUNNING)
    recorder.heartbeat()

    import sqlite3
    with sqlite3.connect(store.database) as connection:
        lease_expires_at = connection.execute(
            "SELECT lease_expires_at FROM compute_jobs WHERE job_id = ?", ("job-1",)
        ).fetchone()[0]

    assert lease_expires_at == renewed.expires_at.isoformat()


@pytest.mark.parametrize(
    ("worker_id", "lease"),
    ((None, object()), ("worker-a", None)),
)
def test_processing_recorder_rejects_incomplete_renewal_configuration(worker_id, lease) -> None:
    with pytest.raises(ValueError, match="renewal requires"):
        ComputeJobProcessingStateRecorder(
            object(),
            job_id="job-1",
            customer_id="user-1",
            project_id="P-1",
            worker_id=worker_id,
            lease=lease,
            renew_lease=lambda: lease,
        )


def test_processing_preserves_heartbeat_lease_loss_when_failed_finish_also_fails(tmp_path) -> None:
    class Recorder:
        def __call__(self, customer_id, project_id, state):
            if state is ProjectProcessingState.FAILED:
                raise PermissionError("compute job worker lease has expired")

        def heartbeat(self):
            raise PermissionError("compute job worker lease has expired")

    recorder = Recorder()
    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: import_result(),
        record_state_for_request=lambda request: recorder,
        import_project_with_heartbeat=lambda directory, heartbeat: heartbeat(),
    )

    with pytest.raises(PermissionError, match="lease has expired") as error:
        service.process(ProjectProcessingRequest("user-1", "P-1", "job-1"))

    assert isinstance(error.value.__cause__, PermissionError)



def test_processing_uses_request_recorder_heartbeat_for_import(tmp_path) -> None:
    events = []

    class Recorder:
        def __call__(self, customer_id, project_id, state):
            events.append(("state", state))

        def heartbeat(self):
            events.append(("heartbeat",))

    recorder = Recorder()

    def import_with_heartbeat(directory, heartbeat):
        assert directory == tmp_path
        assert heartbeat == recorder.heartbeat
        heartbeat()
        return import_result()

    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: (_ for _ in ()).throw(AssertionError("plain import used")),
        record_state_for_request=lambda request: recorder,
        import_project_with_heartbeat=import_with_heartbeat,
    )

    result = service.process(ProjectProcessingRequest("user-1", "P-1", "job-1"))

    assert result.state is ProjectProcessingState.COMPLETED
    assert events == [
        ("state", ProjectProcessingState.RUNNING),
        ("heartbeat",),
        ("state", ProjectProcessingState.COMPLETED),
    ]


def test_processing_uses_recorder_heartbeat_for_persistence(tmp_path) -> None:
    events = []

    class Recorder:
        def __call__(self, customer_id, project_id, state):
            events.append(("state", state))

        def heartbeat(self):
            events.append(("heartbeat",))

    recorder = Recorder()
    imported = import_result()

    def persist_with_heartbeat(customer_id, project_id, result, heartbeat):
        assert (customer_id, project_id, result) == ("user-1", "P-1", imported)
        assert heartbeat == recorder.heartbeat
        heartbeat()
        events.append(("persist",))

    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: imported,
        persist_import=lambda *args: (_ for _ in ()).throw(AssertionError("plain persistence used")),
        record_state_for_request=lambda request: recorder,
        persist_import_with_heartbeat=persist_with_heartbeat,
    )

    result = service.process(ProjectProcessingRequest("user-1", "P-1", "job-1"))

    assert result.state is ProjectProcessingState.COMPLETED
    assert events == [
        ("state", ProjectProcessingState.RUNNING),
        ("heartbeat",),
        ("persist",),
        ("state", ProjectProcessingState.COMPLETED),
    ]


def test_processing_adapts_request_bound_callback_without_heartbeat(tmp_path) -> None:
    states = []
    heartbeat_import_used = []
    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: import_result(),
        record_state_for_request=lambda request: (
            lambda customer_id, project_id, state: states.append(state)
        ),
        import_project_with_heartbeat=lambda directory, heartbeat: (
            heartbeat_import_used.append(True) or heartbeat() or import_result()
        ),
    )

    result = service.process(ProjectProcessingRequest("user-1", "P-1", "job-1"))

    assert result.state is ProjectProcessingState.COMPLETED
    assert heartbeat_import_used == [True]
    assert states == [ProjectProcessingState.RUNNING, ProjectProcessingState.COMPLETED]


def test_processing_stops_persistence_when_lease_heartbeat_fails(tmp_path) -> None:
    events = []

    class Recorder:
        def __call__(self, customer_id, project_id, state):
            events.append(("state", state))

        def heartbeat(self):
            raise PermissionError("worker lease expired")

    recorder = Recorder()

    def persist(customer_id, project_id, imported, heartbeat):
        heartbeat()
        events.append(("persist",))

    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: import_result(),
        record_state_for_request=lambda request: recorder,
        persist_import_with_heartbeat=persist,
    )

    with pytest.raises(PermissionError, match="lease expired"):
        service.process(ProjectProcessingRequest("user-1", "P-1", "job-1"))

    assert events == [
        ("state", ProjectProcessingState.RUNNING),
        ("state", ProjectProcessingState.FAILED),
    ]


def test_processing_adapts_constructor_callback_for_heartbeat_import(tmp_path) -> None:
    states = []
    heartbeat_calls = []

    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: import_result(),
        record_state=lambda customer_id, project_id, state: states.append(state),
        import_project_with_heartbeat=lambda directory, heartbeat: (
            heartbeat_calls.append(heartbeat()) or import_result()
        ),
    )

    result = service.process(ProjectProcessingRequest("user-1", "P-1"))

    assert result.state is ProjectProcessingState.COMPLETED
    assert heartbeat_calls == [None]
    assert states == [ProjectProcessingState.RUNNING, ProjectProcessingState.COMPLETED]


def test_processing_adapts_request_callback_for_heartbeat_persistence(tmp_path) -> None:
    states = []
    persisted = []

    def persist(customer_id, project_id, imported, heartbeat):
        assert heartbeat() is None
        persisted.append((customer_id, project_id, imported))

    imported = import_result()
    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: tmp_path,
        lambda directory: imported,
        record_state_for_request=lambda request: (
            lambda customer_id, project_id, state: states.append(state)
        ),
        persist_import_with_heartbeat=persist,
    )

    result = service.process(ProjectProcessingRequest("user-1", "P-1", "job-1"))

    assert result.state is ProjectProcessingState.COMPLETED
    assert persisted == [("user-1", "P-1", imported)]
    assert states == [ProjectProcessingState.RUNNING, ProjectProcessingState.COMPLETED]
