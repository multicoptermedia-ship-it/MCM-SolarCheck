"""Provider-neutral contracts for an explicitly reviewed PV inspection slice.

No production model, automatic finding, or publication is implied.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol, TypeVar


class VerticalStage(str, Enum):
    IMPORTED = "imported"
    ANALYZED = "analyzed"
    REVIEWED = "reviewed"
    REPORTED = "reported"


@dataclass(frozen=True)
class VerticalProject:
    customer_id: str
    project_id: str
    source_directory: Path

    def __post_init__(self):
        if not self.customer_id.strip() or not self.project_id.strip():
            raise ValueError("customer and project required")
        if not isinstance(self.source_directory, Path):
            raise TypeError("source_directory must be Path")


@dataclass(frozen=True)
class ReviewedDecision:
    reviewer_id: str
    approved: bool
    evidence_reference: str

    def __post_init__(self):
        if not self.reviewer_id.strip() or not self.evidence_reference.strip():
            raise ValueError("reviewer and evidence reference required")
        if type(self.approved) is not bool:
            raise TypeError("approved must be boolean")


class ReviewRequiredError(PermissionError):
    """Report publication is blocked until human approval."""


class StageFunction(Protocol):
    def __call__(self, value: object) -> object: ...


@dataclass(frozen=True)
class VerticalPipelinePorts:
    import_project: Callable[[Path], object]
    analyze_project: Callable[[object], object]
    review_findings: Callable[[object], ReviewedDecision]
    build_report: Callable[[object, ReviewedDecision], object]
