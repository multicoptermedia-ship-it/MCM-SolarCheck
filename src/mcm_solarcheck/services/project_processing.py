"""Application boundary between stored customer uploads and project import."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.services.compute_jobs import ComputeJobStatus


class ProjectProcessingConflict(RuntimeError):
    """The requested project processing is already owned by another worker."""


class ProjectProcessingState(str, Enum):
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ProjectProcessingRequest:
    customer_id: str
    project_id: str
    job_id: str | None = None


@dataclass(frozen=True)
class ProjectProcessingResult:
    customer_id: str
    project_id: str
    state: ProjectProcessingState
    imported_thermal_frames: int
    paired_frames: int
    import_failures: int


class ComputeJobProcessingStateRecorder:
    """Bind one project-processing lifecycle to one authoritative compute job."""

    def __init__(self, jobs, *, job_id: str, customer_id: str, project_id: str, worker_id: str | None = None) -> None:
        self._jobs = jobs
        self._job_id = job_id.strip()
        self._customer_id = customer_id.strip()
        self._project_id = project_id.strip()
        self._worker_id = worker_id.strip() if worker_id is not None else None
        if worker_id is not None and not self._worker_id:
            raise ValueError("worker_id must be a non-empty string")
        if not self._job_id or not self._customer_id or not self._project_id:
            raise ValueError("job, customer and project are required")

    def __call__(
        self,
        customer_id: str,
        project_id: str,
        state: ProjectProcessingState,
    ) -> None:
        if customer_id != self._customer_id or project_id != self._project_id:
            raise PermissionError("processing job identity mismatch")
        if state is ProjectProcessingState.RUNNING:
            try:
                job = self._jobs.get(
                    self._job_id,
                    user_id=self._customer_id,
                    project_id=self._project_id,
                )
            except KeyError as exc:
                raise PermissionError("processing job is not available") from exc
            if job.status is not ComputeJobStatus.RUNNING:
                raise ValueError("compute job must be running before project processing")
            if self._worker_id is not None:
                try:
                    self._jobs.claim(self._job_id, worker_id=self._worker_id)
                except RuntimeError as exc:
                    if "already claimed by another worker" in str(exc):
                        raise ProjectProcessingConflict(
                            "project processing is already running"
                        ) from exc
                    raise
            return
        if state in (ProjectProcessingState.COMPLETED, ProjectProcessingState.FAILED):
            if self._worker_id is not None:
                self._jobs.finish_claimed(
                    self._job_id,
                    worker_id=self._worker_id,
                    succeeded=state is ProjectProcessingState.COMPLETED,
                )
                return
            self._jobs.transition(
                self._job_id,
                (
                    ComputeJobStatus.COMPLETED
                    if state is ProjectProcessingState.COMPLETED
                    else ComputeJobStatus.FAILED
                ),
                user_id=self._customer_id,
                project_id=self._project_id,
            )
            return
        raise ValueError("unsupported project processing state")


class ProjectProcessingService:
    def __init__(
        self,
        project_belongs_to_customer: Callable[[str, str], bool],
        upload_directory_for_project: Callable[[str, str], str | Path],
        import_project: Callable[[str | Path], ProjectImportResult],
        record_state: Callable[[str, str, ProjectProcessingState], None] | None = None,
        persist_import: Callable[[str, str, ProjectImportResult], None] | None = None,
        record_state_for_request: Callable[[ProjectProcessingRequest], Callable[[str, str, ProjectProcessingState], None]] | None = None,
    ) -> None:
        self._project_belongs_to_customer = project_belongs_to_customer
        self._upload_directory_for_project = upload_directory_for_project
        self._import_project = import_project
        self._record_state = record_state
        self._persist_import = persist_import or (lambda customer_id, project_id, imported: None)
        self._record_state_for_request = record_state_for_request

    def process(self, request: ProjectProcessingRequest) -> ProjectProcessingResult:
        customer_id = request.customer_id.strip()
        project_id = request.project_id.strip()
        if not customer_id or not project_id:
            raise ValueError("customer and project are required")
        if not self._project_belongs_to_customer(customer_id, project_id):
            raise PermissionError("project is not available to customer")

        record_state = (
            self._record_state_for_request(request)
            if self._record_state_for_request is not None
            else self._record_state
        )
        if record_state is None:
            raise RuntimeError("project processing state recorder is not configured")
        directory = Path(self._upload_directory_for_project(customer_id, project_id))
        if not directory.is_dir():
            raise ValueError("project upload directory is not available")
        record_state(customer_id, project_id, ProjectProcessingState.RUNNING)
        try:
            imported = self._import_project(directory)
            self._persist_import(customer_id, project_id, imported)
        except Exception as processing_error:
            try:
                record_state(customer_id, project_id, ProjectProcessingState.FAILED)
            except Exception as state_error:
                raise processing_error from state_error
            raise

        record_state(customer_id, project_id, ProjectProcessingState.COMPLETED)
        return ProjectProcessingResult(
            customer_id=customer_id,
            project_id=project_id,
            state=ProjectProcessingState.COMPLETED,
            imported_thermal_frames=len(imported.thermal_batch.results),
            paired_frames=len(imported.pairs),
            import_failures=len(imported.thermal_batch.failures),
        )
