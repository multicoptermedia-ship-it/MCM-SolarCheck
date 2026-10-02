"""Application service for importing one M3T inspection project into SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.importers.project import ProjectImportResult, import_m3t_project
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.storage.queries import InspectionQueries, ProjectRecord
from mcm_solarcheck.services.workflow import ProjectWorkflowService, WorkflowAction, WorkflowAttempt, ProjectWorkflowState, action_availability, record_attempt, require_action
from mcm_solarcheck.services.product_entitlements import ProductCapabilities, ProductOperation, effective_output_availability
from mcm_solarcheck.reporting.export import export_report
from mcm_solarcheck.reporting.report_assembler import assemble_inspection_report
from mcm_solarcheck.review.findings import ReviewStatus, review_finding


@dataclass(frozen=True)
class ProjectPipelineSummary:
    rgb_frames: int
    thermal_frames: int
    thermal_failures: int
    pairs: int
    findings: int
    unpaired_rgb: int
    unpaired_thermal: int


def import_and_store_m3t_project(
    source_directory: str | Path,
    database_path: str | Path,
    *,
    project_id: str,
    project_name: str,
    minimum_pair_confidence: float = 0.70,
    candidate_percentile: float = 99.9,
    candidate_limit: int = 100,
) -> tuple[ProjectImportResult, ProjectPipelineSummary]:
    """Run import, pairing and persistence as one application-level operation."""
    result = import_m3t_project(
        source_directory,
        minimum_pair_confidence=minimum_pair_confidence,
        candidate_percentile=candidate_percentile,
        candidate_limit=candidate_limit,
    )
    database = ProjectDatabase(database_path)
    database.initialize()
    database.create_project(project_id, project_name)
    database.save_image_frames(project_id, result.rgb_frames)
    for thermal in result.thermal_batch.results:
        database.save_thermal_frame(project_id, thermal.frame, thermal.quality)
        database.save_findings(project_id, thermal.findings)
    database.save_pairs(project_id, result.pairs)

    summary = ProjectPipelineSummary(
        rgb_frames=len(result.rgb_frames),
        thermal_frames=len(result.thermal_batch.results),
        thermal_failures=len(result.thermal_batch.failures),
        pairs=len(result.pairs),
        findings=sum(len(item.findings) for item in result.thermal_batch.results),
        unpaired_rgb=result.unpaired_rgb_count,
        unpaired_thermal=result.unpaired_thermal_count,
    )
    return result, summary



class ProjectApplicationService:
    """Guard application operations with the persisted workflow contract."""

    def __init__(self, database: ProjectDatabase) -> None:
        self.database = database
        self.workflow = ProjectWorkflowService(database)

    def projects(self) -> tuple[ProjectRecord, ...]:
        """Expose persisted project selection through the application boundary."""
        return InspectionQueries(self.database).projects()

    def create_project(self, project_id: str, name: str) -> ProjectRecord:
        """Create a new persisted project without silently overwriting an existing one."""
        project_id = project_id.strip()
        name = name.strip()
        if not project_id:
            raise ValueError("project_id must not be blank")
        if not name:
            raise ValueError("name must not be blank")
        if any(project.project_id == project_id for project in self.projects()):
            raise ValueError(f"Project already exists: {project_id}")
        self.database.create_project(project_id, name)
        return next(
            project for project in self.projects() if project.project_id == project_id
        )

    def open_project(self, project_id: str) -> ProjectWorkflowState:
        """Open only a persisted project and return its authoritative workflow state."""
        projects = self.projects()
        if not any(project.project_id == project_id for project in projects):
            raise KeyError(f"Unknown project: {project_id}")
        return self.state(project_id)

    def require(self, project_id: str, action: WorkflowAction) -> None:
        """Reject an operation before side effects when its workflow gate is closed."""
        require_action(self.workflow.state(project_id), action)

    def state(self, project_id: str) -> ProjectWorkflowState:
        """Expose the same persisted state used to guard operations."""
        return self.workflow.state(project_id)

    def execute(self, project_id: str, action: WorkflowAction, operation):
        """Guard, execute once, then re-derive state from persisted evidence."""
        state_before = self.state(project_id)
        require_action(state_before, action)
        try:
            result = operation()
        except Exception as error:
            return record_attempt(action, error), None, self.state(project_id)
        return record_attempt(action), result, self.state(project_id)

    def import_summary(self, project_id: str):
        """Expose persisted import counts through the application boundary."""
        if not any(project.project_id == project_id for project in self.projects()):
            raise KeyError(f"Unknown project: {project_id}")
        return InspectionQueries(self.database).summary(project_id)

    def import_verification(self, project_id: str):
        """Expose persisted import metadata verification through the application boundary."""
        if not any(project.project_id == project_id for project in self.projects()):
            raise KeyError(f"Unknown project: {project_id}")
        return InspectionQueries(self.database).import_verification(project_id)

    def import_project_images(
        self,
        project_id: str,
        source_directory: str | Path,
        *,
        minimum_pair_confidence: float = 0.70,
        candidate_percentile: float = 99.9,
        candidate_limit: int = 100,
    ):
        """Import imagery only through the guarded application boundary."""
        project = next(
            (item for item in self.projects() if item.project_id == project_id),
            None,
        )
        if project is None:
            raise KeyError(f"Unknown project: {project_id}")

        return self.execute(
            project_id,
            WorkflowAction.IMPORT,
            lambda: import_and_store_m3t_project(
                source_directory,
                self.database.path,
                project_id=project.project_id,
                project_name=project.name,
                minimum_pair_confidence=minimum_pair_confidence,
                candidate_percentile=candidate_percentile,
                candidate_limit=candidate_limit,
            ),
        )

    def output_availability(
        self,
        project_id: str,
        capabilities: ProductCapabilities,
        operation: ProductOperation,
    ):
        """Expose one application boundary combining persisted and product gates."""
        workflow_action = (
            WorkflowAction.EXPORT
            if operation is ProductOperation.EXPORT
            else WorkflowAction.PREPARE_REPORT
        )
        workflow = action_availability(self.state(project_id), workflow_action)
        return effective_output_availability(
            capabilities,
            operation,
            workflow_allowed=workflow.allowed,
            workflow_blockers=workflow.blockers,
        )



    def review_finding(
        self,
        project_id: str,
        finding,
        *,
        status: ReviewStatus,
        reviewer: str,
        note: str | None = None,
        reviewed_at_utc=None,
    ):
        """Apply and persist a human review only through the workflow boundary."""
        self.require(project_id, WorkflowAction.REVIEW)
        reviewed, audit = review_finding(
            finding,
            status=status,
            reviewer=reviewer,
            note=note,
            reviewed_at_utc=reviewed_at_utc,
        )
        self.database.save_review(audit, project_id=project_id)
        return reviewed, audit, self.state(project_id)


    def prepare_report(
        self,
        project_id: str,
        report_id: str,
        inspection_started_at,
        *,
        release_status: str = "draft",
        asset_dir=None,
        operator_profile=None,
    ):
        """Assemble a report only when persisted workflow evidence permits it."""
        self.require(project_id, WorkflowAction.PREPARE_REPORT)
        return assemble_inspection_report(
            self.database,
            project_id,
            report_id,
            inspection_started_at,
            release_status=release_status,
            asset_dir=asset_dir,
            operator_profile=operator_profile,
        )


    def export_report(
        self,
        project_id: str,
        capabilities: ProductCapabilities,
        report,
        destination: str | Path,
        *,
        format: str | None = None,
        banner_path: str | Path | None = None,
    ):
        """Export only after both persisted workflow and product gates allow it."""
        availability = self.output_availability(
            project_id, capabilities, ProductOperation.EXPORT
        )
        if not availability.allowed:
            reasons = "; ".join(availability.blockers)
            raise ValueError(f"export action is blocked: {reasons}")
        return export_report(
            report,
            destination,
            format=format,
            banner_path=banner_path,
        )
