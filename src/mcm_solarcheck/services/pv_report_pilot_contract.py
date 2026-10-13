"""Shared offline/online content contract for an expert-reviewed customer pilot report."""
from dataclasses import dataclass
from math import isfinite

from mcm_solarcheck.services.pv_pilot_ai_assessment import PilotAIAssessment


@dataclass(frozen=True)
class PilotFinding:
    module: str
    observation: str
    reviewed: bool = False
    ai_assessment: PilotAIAssessment | None = None

    def __post_init__(self):
        if self.ai_assessment is not None and not isinstance(self.ai_assessment, PilotAIAssessment):
            raise TypeError("PilotAIAssessment required")


@dataclass(frozen=True)
class PilotReport:
    project: str
    inspection_date: str
    inspector: str
    plant: str
    conditions: str | None
    limitations: str
    findings: tuple[PilotFinding, ...]
    site_address: str | None = None
    total_modules: int | None = None
    conspicuous_modules: int | None = None
    irradiance_w_m2: float | None = None
    irradiance_source: str | None = None

    def __post_init__(self):
        if not all((self.project.strip(), self.inspection_date.strip(),
                    self.inspector.strip(), self.plant.strip(), self.limitations.strip())):
            raise ValueError("required report details missing")
        for name, count in (("total_modules", self.total_modules), ("conspicuous_modules", self.conspicuous_modules)):
            if count is not None and (isinstance(count, bool) or not isinstance(count, int) or count < 0):
                raise ValueError(f"{name} must be a non-negative integer")
        if self.total_modules is not None and self.conspicuous_modules is not None and self.conspicuous_modules > self.total_modules:
            raise ValueError("conspicuous modules cannot exceed inspected modules")
        if self.irradiance_w_m2 is not None and (isinstance(self.irradiance_w_m2, bool) or not isinstance(self.irradiance_w_m2, (int, float)) or not isfinite(self.irradiance_w_m2) or self.irradiance_w_m2 < 0):
            raise ValueError("irradiance must be a finite non-negative number")
        if self.site_address is not None and not self.site_address.strip():
            raise ValueError("site address must not be blank")
        if self.irradiance_source is not None and not self.irradiance_source.strip():
            raise ValueError("irradiance source must not be blank")
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
        ("Anlagenadresse", report.site_address or "nicht erfasst"),
        ("Geprüfte Module", str(report.total_modules) if report.total_modules is not None else "nicht erfasst"),
        ("Auffällige Module", str(report.conspicuous_modules) if report.conspicuous_modules is not None else "nicht erfasst"),
        ("Einstrahlungsstärke zum Messzeitpunkt", f"{report.irradiance_w_m2:g} W/m²; Quelle: {report.irradiance_source or 'nicht erfasst'}" if report.irradiance_w_m2 is not None else "nicht erfasst"),
        ("Prüfbedingungen", report.conditions or "nicht erfasst"),
        ("Feststellungen", observations),
        ("Einschränkungen", report.limitations),
        ("Hinweis", "Thermische Auffälligkeiten allein belegen keine elektrische Fehlerursache."),
    )
