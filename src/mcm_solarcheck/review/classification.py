"""Provider boundary for machine-assisted Phase 7 defect classification.

Classifier output is advisory evidence only. A human review remains authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from mcm_solarcheck.domain.models import Finding


@dataclass(frozen=True)
class DefectClassification:
    label: str
    confidence: float
    provider: str
    model_version: str | None = None
    modality: str | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("classification label must not be empty")
        if not self.provider.strip():
            raise ValueError("classification provider must not be empty")
        if not isfinite(float(self.confidence)) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("classification confidence must be finite and between 0 and 1")
        if self.modality is not None and self.modality not in {"thermal", "rgb"}:
            raise ValueError("classification modality must be thermal or rgb")


class DefectClassifier(Protocol):
    @property
    def name(self) -> str: ...

    def classify(self, finding: Finding) -> DefectClassification: ...


def attach_classification_suggestion(
    finding: Finding,
    suggestion: DefectClassification,
) -> Finding:
    """Attach auditable machine evidence without changing the human review state."""
    from dataclasses import replace

    metadata = dict(finding.metadata)
    metadata.update({
        "classification_status": "suggested",
        "classification_label": suggestion.label.strip(),
        "classification_confidence": str(float(suggestion.confidence)),
        "classification_provider": suggestion.provider.strip(),
    })
    if suggestion.model_version:
        metadata["classification_model_version"] = suggestion.model_version.strip()
    if suggestion.modality:
        metadata["classification_modality"] = suggestion.modality
    return replace(finding, metadata=metadata)
