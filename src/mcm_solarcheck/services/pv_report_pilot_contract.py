"""Shared offline/online content contract for an expert-reviewed customer pilot report."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PilotFinding:
    module: str
    observation: str
    reviewed: bool = False


@dataclass(frozen=True)
class PilotReport:
    project: str
    inspection_date: str
    inspector: str
    plant: str
    conditions: str | None
    limitations: str
    findings: tuple[PilotFinding, ...]

    def __post_init__(self):
        if not all((self.project.strip(), self.inspection_date.strip(),
                    self.inspector.strip(), self.plant.strip(), self.limitations.strip())):
            raise ValueError("required report details missing")
        if any(not finding.reviewed for finding in self.findings):
            raise PermissionError("findings require expert review")


def report_sections(report: PilotReport) -> tuple[tuple[str, str], ...]:
    observations = "\n".join(
        f"{f.module}: {f.observation}" for f in report.findings
    ) or "Keine fachlich bestätigten Auffälligkeiten dokumentiert."
    return (
        ("Titel", "SolarCheck – Prüfbericht (Kundenmuster)"),
        ("Grundlage", "In Anlehnung an DIN IEC/TS 62446-3 (VDE V 0126-23-3):2018-04; kein Normkonformitätsnachweis."),
        ("Projekt", report.project),
        ("Prüfdatum", report.inspection_date),
        ("Prüfer", report.inspector),
        ("Anlage", report.plant),
        ("Prüfbedingungen", report.conditions or "nicht erfasst"),
        ("Feststellungen", observations),
        ("Einschränkungen", report.limitations),
        ("Hinweis", "Thermische Auffälligkeiten allein belegen keine elektrische Fehlerursache."),
    )
