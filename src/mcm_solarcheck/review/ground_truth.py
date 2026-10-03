"""Human-reviewed ground truth for future MCM model training."""
from __future__ import annotations
from dataclasses import dataclass
from .defect_classes import DefectClass


@dataclass(frozen=True)
class GroundTruthLabel:
    source_frame_id: str
    reviewer: str
    defect_class: DefectClass
    module_id: str | None = None
    finding_id: str | None = None
    supersedes_label_id: int | None = None
    note: str | None = None
    inspection_group_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_frame_id,str) or not self.source_frame_id.strip():
            raise ValueError("ground-truth source frame must not be empty")
        if not isinstance(self.reviewer,str) or not self.reviewer.strip():
            raise ValueError("ground-truth reviewer must not be empty")
        if self.module_id is None and self.finding_id is None:
            raise ValueError("ground truth must reference a module or finding")
        if self.supersedes_label_id is not None and self.supersedes_label_id < 1:
            raise ValueError("superseded label id must be positive")
        if self.note is not None and (not isinstance(self.note,str) or not self.note.strip()):
            raise ValueError("ground-truth note must not be blank")
        if self.inspection_group_id is not None and (not isinstance(self.inspection_group_id,str) or not self.inspection_group_id.strip()):
            raise ValueError("inspection group id must not be blank")
