"""Backend-neutral application workflow contract for Phase 10."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkflowAction(str, Enum):
    IMPORT = "import"
    PROCESS = "process"
    REVIEW = "review"
    PREPARE_REPORT = "prepare_report"
    EXPORT = "export"


class WorkflowStage(str, Enum):
    PROJECT = "project"
    IMPORT = "import"
    PROCESSING = "processing"
    REVIEW = "review"
    REPORT = "report"
    EXPORT = "export"


@dataclass(frozen=True)
class StageReadiness:
    stage: WorkflowStage
    ready: bool
    blockers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.stage, WorkflowStage):
            raise ValueError("stage must be a WorkflowStage")
        if type(self.ready) is not bool:
            raise ValueError("ready must be bool")
        blockers = tuple(self.blockers)
        if any(not isinstance(item, str) or not item.strip() for item in blockers):
            raise ValueError("blockers must contain non-empty strings")
        if self.ready and blockers:
            raise ValueError("ready stage must not have blockers")
        if not self.ready and not blockers:
            raise ValueError("blocked stage requires at least one blocker")
        object.__setattr__(self, "blockers", blockers)


@dataclass(frozen=True)
class ProjectWorkflowState:
    stages: tuple[StageReadiness, ...]

    def __post_init__(self) -> None:
        stages = tuple(self.stages)
        if not stages:
            raise ValueError("workflow state requires stages")
        identities = tuple(item.stage for item in stages)
        if len(set(identities)) != len(identities):
            raise ValueError("workflow stages must be unique")
        object.__setattr__(self, "stages", stages)

    def readiness(self, stage: WorkflowStage) -> StageReadiness:
        for item in self.stages:
            if item.stage is stage:
                return item
        raise KeyError(stage)


class ProjectWorkflowService:
    """Derive application readiness from persisted inspection evidence."""

    def __init__(self, database) -> None:
        from mcm_solarcheck.storage.queries import InspectionQueries
        self.database = database
        self.queries = InspectionQueries(database)

    def state(self, project_id: str) -> ProjectWorkflowState:
        summary = self.queries.summary(project_id)
        has_images = summary.rgb_frames > 0 or summary.thermal_frames > 0
        has_processing = summary.pv_modules > 0 or summary.findings > 0
        review_blockers = []
        if not has_processing:
            review_blockers.append("no processed modules or findings")
        report_blockers = []
        if summary.unreviewed_findings:
            report_blockers.append("unreviewed findings remain")
        findings = self.queries.findings(project_id)
        unresolved_reviewed = sum(
            1
            for item in findings
            if item.reviewer_status in ("confirmed", "unclear")
            and (item.module_id is None or not item.module_id.strip())
        )
        if unresolved_reviewed:
            report_blockers.append("reviewed findings require resolved physical modules")
        if not has_processing:
            report_blockers.append("no processed modules or findings")
        export_blockers = list(report_blockers)
        stages = (
            StageReadiness(WorkflowStage.PROJECT, True),
            StageReadiness(WorkflowStage.IMPORT, True if has_images else False, () if has_images else ("no imported image frames",)),
            StageReadiness(WorkflowStage.PROCESSING, True if has_images else False, () if has_images else ("import required before processing",)),
            StageReadiness(WorkflowStage.REVIEW, not review_blockers, tuple(review_blockers)),
            StageReadiness(WorkflowStage.REPORT, not report_blockers, tuple(report_blockers)),
            StageReadiness(WorkflowStage.EXPORT, not export_blockers, tuple(export_blockers)),
        )
        return ProjectWorkflowState(stages)


@dataclass(frozen=True)
class WorkflowResumePoint:
    stage: WorkflowStage
    blockers: tuple[str, ...] = ()


def resume_point(state: ProjectWorkflowState) -> WorkflowResumePoint:
    """Return the first stage that still needs work, without inventing UI state."""
    order = (
        WorkflowStage.IMPORT,
        WorkflowStage.PROCESSING,
        WorkflowStage.REVIEW,
        WorkflowStage.REPORT,
        WorkflowStage.EXPORT,
    )
    for stage in order:
        readiness = state.readiness(stage)
        if not readiness.ready:
            return WorkflowResumePoint(stage, readiness.blockers)
    return WorkflowResumePoint(WorkflowStage.EXPORT)


_ACTION_STAGE = {
    WorkflowAction.IMPORT: WorkflowStage.PROJECT,
    WorkflowAction.PROCESS: WorkflowStage.IMPORT,
    WorkflowAction.REVIEW: WorkflowStage.REVIEW,
    WorkflowAction.PREPARE_REPORT: WorkflowStage.REPORT,
    WorkflowAction.EXPORT: WorkflowStage.EXPORT,
}


@dataclass(frozen=True)
class ActionAvailability:
    action: WorkflowAction
    allowed: bool
    blockers: tuple[str, ...] = ()


def action_availability(
    state: ProjectWorkflowState, action: WorkflowAction
) -> ActionAvailability:
    """Derive whether an application action may run from persisted readiness."""
    if not isinstance(action, WorkflowAction):
        raise ValueError("action must be a WorkflowAction")
    readiness = state.readiness(_ACTION_STAGE[action])
    return ActionAvailability(action, readiness.ready, readiness.blockers)


def require_action(state: ProjectWorkflowState, action: WorkflowAction) -> None:
    """Fail closed before an application service executes a blocked action."""
    availability = action_availability(state, action)
    if not availability.allowed:
        reasons = "; ".join(availability.blockers)
        raise ValueError(f"{action.value} action is blocked: {reasons}")
