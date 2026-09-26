"""Application service for importing one M3T inspection project into SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.importers.project import ProjectImportResult, import_m3t_project
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.services.workflow import ProjectWorkflowService, WorkflowAction, WorkflowAttempt, ProjectWorkflowState, action_availability, record_attempt, require_action
from mcm_solarcheck.services.product_entitlements import ProductCapabilities, ProductOperation, effective_output_availability


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
