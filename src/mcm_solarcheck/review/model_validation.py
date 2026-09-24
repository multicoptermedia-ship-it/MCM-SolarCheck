"""Validation policy for admitting pretrained models into customer projects."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ModelValidationSummary:
    sample_count: int
    defect_sample_count: int
    matched_defect_count: int
    false_positive_count: int
    representative_m3t: bool
    reviewer: str

    def __post_init__(self) -> None:
        counts=(self.sample_count,self.defect_sample_count,self.matched_defect_count,self.false_positive_count)
        if any(type(v) is not int or v < 0 for v in counts):
            raise ValueError("validation counts must be non-negative integers")
        if self.sample_count == 0:
            raise ValueError("validation requires at least one sample")
        if self.defect_sample_count > self.sample_count:
            raise ValueError("defect samples cannot exceed total samples")
        if self.matched_defect_count > self.defect_sample_count:
            raise ValueError("matched defects cannot exceed defect samples")
        if self.false_positive_count > self.sample_count:
            raise ValueError("false positives cannot exceed total samples")
        if not self.reviewer.strip():
            raise ValueError("validation reviewer must not be empty")

    @property
    def recall(self) -> float | None:
        if self.defect_sample_count == 0:
            return None
        return self.matched_defect_count / self.defect_sample_count

    @property
    def false_positive_rate(self) -> float:
        return self.false_positive_count / self.sample_count


@dataclass(frozen=True)
class ModelAcceptancePolicy:
    min_samples: int = 20
    min_defect_samples: int = 5
    min_recall: float = 0.70
    max_false_positive_rate: float = 0.25

    def __post_init__(self) -> None:
        if self.min_samples < 1 or self.min_defect_samples < 1:
            raise ValueError("acceptance sample minima must be positive")
        for name,value in (("min_recall",self.min_recall),("max_false_positive_rate",self.max_false_positive_rate)):
            if not isfinite(float(value)) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and between 0 and 1")

    def accepts(self, summary: ModelValidationSummary) -> bool:
        return (
            summary.representative_m3t
            and summary.sample_count >= self.min_samples
            and summary.defect_sample_count >= self.min_defect_samples
            and summary.recall is not None
            and summary.recall >= self.min_recall
            and summary.false_positive_rate <= self.max_false_positive_rate
        )


@dataclass(frozen=True)
class ModelValidationDecision:
    accepted: bool
    reasons: tuple[str, ...]


def evaluate_model(
    summary: ModelValidationSummary,
    policy: ModelAcceptancePolicy | None = None,
) -> ModelValidationDecision:
    """Explain every failed acceptance condition for audit and UI display."""
    policy=policy or ModelAcceptancePolicy()
    reasons=[]
    if not summary.representative_m3t:
        reasons.append("validation imagery is not representative M3T data")
    if summary.sample_count < policy.min_samples:
        reasons.append("insufficient validation samples")
    if summary.defect_sample_count < policy.min_defect_samples:
        reasons.append("insufficient defect samples")
    if summary.recall is None or summary.recall < policy.min_recall:
        reasons.append("defect recall below acceptance threshold")
    if summary.false_positive_rate > policy.max_false_positive_rate:
        reasons.append("false-positive rate above acceptance threshold")
    return ModelValidationDecision(not reasons, tuple(reasons))
