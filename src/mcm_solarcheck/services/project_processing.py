"""Application boundary between stored customer uploads and project import."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

from mcm_solarcheck.importers.project import ProjectImportResult


class ProjectProcessingState(str, Enum):
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ProjectProcessingRequest:
    customer_id: str
    project_id: str


@dataclass(frozen=True)
class ProjectProcessingResult:
    customer_id: str
    project_id: str
    state: ProjectProcessingState
    imported_thermal_frames: int
    paired_frames: int
    import_failures: int


class ProjectProcessingService:
    def __init__(
        self,
        project_belongs_to_customer: Callable[[str, str], bool],
        upload_directory_for_project: Callable[[str, str], str | Path],
        import_project: Callable[[str | Path], ProjectImportResult],
        record_state: Callable[[str, str, ProjectProcessingState], None],
    ) -> None:
        self._project_belongs_to_customer = project_belongs_to_customer
        self._upload_directory_for_project = upload_directory_for_project
        self._import_project = import_project
        self._record_state = record_state

    def process(self, request: ProjectProcessingRequest) -> ProjectProcessingResult:
        customer_id = request.customer_id.strip()
        project_id = request.project_id.strip()
        if not customer_id or not project_id:
            raise ValueError("customer and project are required")
        if not self._project_belongs_to_customer(customer_id, project_id):
            raise PermissionError("project is not available to customer")

        directory = Path(self._upload_directory_for_project(customer_id, project_id))
        if not directory.is_dir():
            raise ValueError("project upload directory is not available")
        self._record_state(customer_id, project_id, ProjectProcessingState.RUNNING)
        try:
            imported = self._import_project(directory)
        except Exception:
            self._record_state(customer_id, project_id, ProjectProcessingState.FAILED)
            raise

        self._record_state(customer_id, project_id, ProjectProcessingState.COMPLETED)
        return ProjectProcessingResult(
            customer_id=customer_id,
            project_id=project_id,
            state=ProjectProcessingState.COMPLETED,
            imported_thermal_frames=len(imported.thermal_batch.results),
            paired_frames=len(imported.pairs),
            import_failures=len(imported.thermal_batch.failures),
        )
