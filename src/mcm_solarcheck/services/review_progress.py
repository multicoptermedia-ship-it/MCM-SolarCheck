"""Advisory inspection decision progress derived from persisted project counts.

This is not a readiness gate, an approval, or proof that every flight image
was correctly imported. The authoritative report and export gates stay in
the application service and workflow.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.storage.queries import InspectionSummary


@dataclass(frozen=True)
class ReviewProgress:
    """A non-mutating, project-scoped status snapshot for desktop display."""
    project_id: str
    total_findings: int
    decided_findings: int
    open_findings: int
    confirmed_findings: int
    rejected_findings: int
    unclear_findings: int
    other_status_findings: int
    decision_percent: int
    all_findings_decided: bool
    guidance: tuple[str, ...]


def derive_review_progress(summary: InspectionSummary) -> ReviewProgress:
    """Distinguish explicit decisions from open or unrecognized records."""
    if not isinstance(summary, InspectionSummary):
        raise TypeError("persisted inspection summary required")
    total = summary.findings
    counts = (
        summary.unreviewed_findings,
        summary.confirmed_findings,
        summary.rejected_findings,
        summary.unclear_findings,
    )
    if (
        type(total) is not int or total < 0
        or any(type(count) is not int or count < 0 for count in counts)
        or sum(counts) > total
    ):
        raise ValueError("inconsistent persisted finding status counts")
    open_count, confirmed, rejected, unclear = counts
    decided = confirmed + rejected + unclear
    other = total - sum(counts)
    percent = (decided * 100 // total) if total else 0
    steps: list[str] = []
    if total == 0:
        steps.append(
            "Noch keine Befundkandidaten gespeichert. Daraus lässt sich "
            "weder eine abgeschlossene Bildauswertung noch eine mängelfreie "
            "Anlage ableiten."
        )
    if open_count:
        steps.append(
            f"{open_count} offene Befunde benötigen jeweils eine ausdrückliche "
            "menschliche Entscheidung."
        )
    if other:
        steps.append(
            f"{other} Befunde haben keinen bekannten Prüfstatus. "
            "Datensatz und Projektzustand fachlich prüfen."
        )
    if unclear:
        steps.append(
            f"{unclear} Befunde wurden als unklar dokumentiert; "
            "Nachprüfung gegebenenfalls separat veranlassen. "
            "Unklar bedeutet nicht bestätigt oder mängelfrei."
        )
    if not steps:
        steps.append(
            "Alle gespeicherten Befundkandidaten haben eine fachliche "
            "Entscheidung. Bild- und Modulnachweise sowie die gesonderten "
            "Berichtsberechtigungen weiterhin prüfen."
        )
    steps.append(
        "Nur Statusübersicht aus SQLite; keine automatische Diagnose, "
        "Normkonformität, Berichtsfreigabe oder Exportberechtigung."
    )
    return ReviewProgress(
        project_id=summary.project_id,
        total_findings=total,
        decided_findings=decided,
        open_findings=open_count,
        confirmed_findings=confirmed,
        rejected_findings=rejected,
        unclear_findings=unclear,
        other_status_findings=other,
        decision_percent=percent,
        all_findings_decided=bool(total and not open_count and not other),
        guidance=tuple(steps),
    )
