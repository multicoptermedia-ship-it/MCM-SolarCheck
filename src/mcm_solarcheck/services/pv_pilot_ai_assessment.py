"""Conservative AI classification contract; never equate model output with diagnosis."""
from dataclasses import dataclass

from mcm_solarcheck.services.pv_pilot_ai_provenance import PilotAIProvenance


@dataclass(frozen=True)
class PilotAIAssessment:
    status: str  # classified_suspicion, unassigned, no_anomaly
    suggested_cause: str | None = None
    expert_assessment: str | None = None
    provenance: PilotAIProvenance | None = None

    def __post_init__(self):
        if self.provenance is not None and not isinstance(self.provenance, PilotAIProvenance):
            raise TypeError("PilotAIProvenance required")
        if self.status not in {"classified_suspicion", "unassigned", "no_anomaly"}:
            raise ValueError("unsupported AI assessment status")
        if self.status == "classified_suspicion" and (
            not isinstance(self.suggested_cause, str) or not self.suggested_cause.strip()
        ):
            raise ValueError("classified suspicion requires a cause label")
        if self.status != "classified_suspicion" and self.suggested_cause is not None:
            raise ValueError("cause label only allowed for classified suspicion")
        if self.expert_assessment is not None and (
            not isinstance(self.expert_assessment, str) or not self.expert_assessment.strip()
        ):
            raise ValueError("expert assessment must not be blank")


def ai_display(assessment: PilotAIAssessment | None) -> str:
    if assessment is None:
        return "KI-Klassifizierung: nicht erfasst"
    if assessment.status == "classified_suspicion":
        return f"KI-Klassifizierung: Verdacht auf {assessment.suggested_cause}"
    if assessment.status == "unassigned":
        return "KI-Klassifizierung: Auffälligkeit erkannt - Ursache nicht eindeutig zuzuordnen"
    return "KI-Klassifizierung: Keine Auffälligkeit erkannt"


def expert_display(assessment: PilotAIAssessment | None) -> str:
    if assessment is None or assessment.expert_assessment is None:
        return "Fachliche Bewertung: nicht dokumentiert"
    return "Fachliche Bewertung: " + assessment.expert_assessment
