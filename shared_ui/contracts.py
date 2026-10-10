"""Presentation-only contracts; permissions and analysis remain authoritative in services."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class RuntimeMode(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass(frozen=True)
class RuntimeInfo:
    mode: RuntimeMode
    features_ready: bool = False

    def to_dict(self) -> dict:
        return {"mode": self.mode.value, "features_ready": self.features_ready}


@dataclass(frozen=True)
class FindingView:
    module_id: str
    finding_type: str
    confidence: float | None
    review_status: str

    def __post_init__(self):
        if not self.module_id.strip() or not self.finding_type.strip():
            raise ValueError("module and finding type are required")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict:
        return asdict(self)
