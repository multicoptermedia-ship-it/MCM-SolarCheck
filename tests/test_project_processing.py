from pathlib import Path
from types import SimpleNamespace

import pytest

from mcm_solarcheck.services.project_processing import (
    ProjectProcessingRequest,
    ProjectProcessingService,
    ProjectProcessingState,
)


def import_result(*, imported=2, paired=1, failures=0):
    return SimpleNamespace(
        thermal_batch=SimpleNamespace(
            results=tuple(object() for _ in range(imported)),
            failures=tuple(object() for _ in range(failures)),
        ),
        pairs=tuple(object() for _ in range(paired)),
    )


def test_processing_resolves_customer_project_uploads_and_records_lifecycle() -> None:
    states = []
    imported_directories = []
    service = ProjectProcessingService(
        lambda customer_id, project_id: (customer_id, project_id) == ("user-1", "P-1"),
        lambda customer_id, project_id: Path("/stored/user-1/P-1"),
        lambda directory: imported_directories.append(directory) or import_result(),
        lambda customer_id, project_id, state: states.append((customer_id, project_id, state)),
    )

    result = service.process(ProjectProcessingRequest("user-1", "P-1"))

    assert imported_directories == [Path("/stored/user-1/P-1")]
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


def test_processing_records_failed_state_when_import_raises() -> None:
    states = []

    def fail_import(directory):
        raise RuntimeError("import failed")

    service = ProjectProcessingService(
        lambda customer_id, project_id: True,
        lambda customer_id, project_id: Path("/stored/user-1/P-1"),
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
