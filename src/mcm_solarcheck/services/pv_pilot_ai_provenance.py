"""Auditable model metadata and explicit human decision; no inference is run here."""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class PilotAIProvenance:
    model_id: str
    model_version: str
    input_reference: str
    confidence: float | None = None
    reviewer_decision: str = "pending"  # pending, accepted, corrected, rejected

    def __post_init__(self):
        for name in ("model_id", "model_version", "input_reference"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} required")
        if self.confidence is not None and (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not isfinite(self.confidence)
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be a finite fraction from 0 to 1")
        if self.reviewer_decision not in {"pending", "accepted", "corrected", "rejected"}:
            raise ValueError("unsupported reviewer decision")


def provenance_display(provenance: PilotAIProvenance | None) -> tuple[str, ...]:
    if provenance is None:
        return ("KI-Modellnachweis: nicht erfasst",)
    confidence = ("nicht erfasst" if provenance.confidence is None
                  else f"{provenance.confidence * 100:.1f} % (Modellwert, nicht Diagnosewahrscheinlichkeit)")
    decisions = {"pending": "ausstehend", "accepted": "übernommen",
                 "corrected": "korrigiert", "rejected": "verworfen"}
    return (
        f"KI-Modell: {provenance.model_id}; Version: {provenance.model_version}",
        f"KI-Eingabequelle: {provenance.input_reference}",
        f"KI-Konfidenz: {confidence}",
        f"Prüferentscheidung zum KI-Vorschlag: {decisions[provenance.reviewer_decision]}",
    )
