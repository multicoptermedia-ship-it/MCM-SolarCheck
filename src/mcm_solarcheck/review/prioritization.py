"""Conservative Phase 6 finding prioritization.

Priority is an ordering aid for expert review, not a defect classification.
Only calibrated temperature evidence may influence thermal severity. Raw
radiometric values deliberately remain unscored.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.thermal.temperature_provenance import has_validated_celsius


@dataclass(frozen=True)
class FindingPriority:
    finding_id: str
    level: str
    score: float | None
    reason: str


def prioritize_finding(finding: Finding) -> FindingPriority:
    """Return an auditable review priority without inventing missing evidence."""
    if finding.temperature_c is None:
        return FindingPriority(finding.finding_id, "unrated", None, "calibrated_temperature_required")
    status=finding.metadata.get("temperature_status")
    provider=finding.metadata.get("temperature_provider")
    if status != "calibrated" or not provider or not provider.strip():
        return FindingPriority(finding.finding_id, "unrated", None, "temperature_provenance_required")
    if not has_validated_celsius(finding.temperature_c, status, provider):
        return FindingPriority(finding.finding_id, "unrated", None, "invalid_temperature")
    if finding.confidence is None:
        return FindingPriority(finding.finding_id, "unrated", None, "confidence_required")
    if not isfinite(float(finding.confidence)) or not 0.0 <= finding.confidence <= 1.0:
        return FindingPriority(finding.finding_id, "unrated", None, "invalid_confidence")

    # Until a validated thermal severity model is introduced, calibrated
    # temperature is retained as evidence but does not imply a defect threshold.
    return FindingPriority(finding.finding_id, "review", float(finding.confidence), "calibrated_evidence_available")


def prioritize_findings(findings: tuple[Finding, ...]) -> tuple[FindingPriority, ...]:
    """Return deterministic review order without turning raw evidence into severity."""
    priorities = tuple(prioritize_finding(finding) for finding in findings)
    return tuple(sorted(
        priorities,
        key=lambda item: (
            item.level != "review",
            -(item.score if item.score is not None else -1.0),
            item.finding_id,
        ),
    ))
