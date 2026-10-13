"""Validate local detector output before human review; never release automatically."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.pv_pilot_ai_assessment import PilotAIAssessment
from mcm_solarcheck.services.pv_pilot_ai_provenance import PilotAIProvenance


@dataclass(frozen=True)
class LocalAIResult:
    module: str
    status: str
    model_id: str
    model_version: str
    input_reference: str
    suggested_cause: str | None = None
    confidence: float | None = None

    def __post_init__(self):
        if not isinstance(self.module, str) or not self.module.strip():
            raise ValueError("module required")


def stage_local_ai_result(result: LocalAIResult) -> PilotAIAssessment:
    """Stage an unapproved suggestion with explicit pending decision."""
    if not isinstance(result, LocalAIResult):
        raise TypeError("LocalAIResult required")
    provenance = PilotAIProvenance(
        model_id=result.model_id,
        model_version=result.model_version,
        input_reference=result.input_reference,
        confidence=result.confidence,
        reviewer_decision="pending",
    )
    return PilotAIAssessment(
        status=result.status,
        suggested_cause=result.suggested_cause,
        provenance=provenance,
    )
