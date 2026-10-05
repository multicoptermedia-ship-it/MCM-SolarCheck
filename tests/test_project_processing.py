from pathlib import Path
from types import SimpleNamespace

import pytest

from mcm_solarcheck.services.project_processing import (
    ProjectProcessingRequest,
    ProjectProcessingService,
    ProjectProcessingState,
    ComputeJobProcessingStateRecorder,
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
