"""Offline-first bridge from validated local AI suggestions to review candidates.

No inference, approval, report export, or network operation occurs here.
The resulting shared-domain findings can be reviewed by offline and online UIs.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.services.pv_pilot_ai_ingestion import LocalAIResult, stage_local_ai_result
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis


@dataclass(frozen=True)
class LocalAICandidate:
    finding_id: str
    thermal_frame_id: str
    pixel_x: int
    pixel_y: int
    result: LocalAIResult


def stage_local_ai_candidates(
    analysis: ImportedCandidateAnalysis,
    detections: tuple[LocalAICandidate, ...],
) -> ImportedCandidateAnalysis:
    """Append validated, explicitly unreviewed AI candidates to paired evidence."""
    if not isinstance(analysis, ImportedCandidateAnalysis):
        raise TypeError("ImportedCandidateAnalysis required")
    if not isinstance(detections, tuple):
        raise TypeError("detections must be a tuple")
    existing = {f.finding_id for f in analysis.candidates}
    if len(existing) != len(analysis.candidates):
        raise ValueError("duplicate existing finding IDs")
    if analysis.paired_frames < 1 or analysis.imported_thermal_frames < 1:
        raise ValueError("paired RGB and thermal evidence required")
    known_thermal_frames = {f.thermal_frame_id for f in analysis.candidates}
    findings = list(analysis.candidates)
    for candidate in detections:
        if not isinstance(candidate, LocalAICandidate):
            raise TypeError("LocalAICandidate required")
        for name in ("finding_id", "thermal_frame_id"):
            value = getattr(candidate, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} required")
        if candidate.finding_id in existing:
            raise ValueError("duplicate candidate identifier")
        for name in ("pixel_x", "pixel_y"):
            value = getattr(candidate, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        staged = stage_local_ai_result(candidate.result)
        if candidate.thermal_frame_id not in known_thermal_frames:
            raise ValueError("AI source must reference known imported thermal evidence")
        if staged.provenance.input_reference != candidate.thermal_frame_id:
            raise ValueError("AI input reference must match thermal frame")
        existing.add(candidate.finding_id)
        findings.append(Finding(
            finding_id=candidate.finding_id,
            thermal_frame_id=candidate.thermal_frame_id,
            pixel_x=candidate.pixel_x,
            pixel_y=candidate.pixel_y,
            finding_type="local_ai_suggestion_unverified",
            confidence=staged.provenance.confidence,
            module_id=candidate.result.module,
            reviewer_status="unreviewed",
        ))
    return ImportedCandidateAnalysis(
        paired_frames=analysis.paired_frames,
        imported_thermal_frames=analysis.imported_thermal_frames,
        candidates=tuple(findings),
        source=analysis.source,
    )
