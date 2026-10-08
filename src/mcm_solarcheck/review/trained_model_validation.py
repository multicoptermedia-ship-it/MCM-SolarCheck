"""Validation and release gate for MCM-trained model artifacts."""
from __future__ import annotations
from dataclasses import dataclass

from .model_lineage import TrainedModelArtifact
from .model_validation import ModelValidationDecision


@dataclass(frozen=True)
class TrainedModelValidation:
    artifact: TrainedModelArtifact
    decision: ModelValidationDecision
    evaluator: str

    def __post_init__(self) -> None:
        if not isinstance(self.evaluator,str) or not self.evaluator.strip():
            raise ValueError("model evaluator must not be empty")

    @property
    def releasable(self) -> bool:
        return self.decision.accepted


def require_trained_model_validation(value: TrainedModelValidation) -> None:
    if not value.decision.accepted:
        reasons="; ".join(value.decision.reasons) or "validation not accepted"
        raise ValueError(f"trained model failed validation: {reasons}")
