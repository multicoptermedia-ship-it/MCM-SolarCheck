"""Backend-neutral application workflow contract for Phase 10."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
