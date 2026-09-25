"""Shared presentation semantics for editable/final report renderers."""
from __future__ import annotations
from dataclasses import dataclass
from .report_model import InspectionReport, ModuleReportDetail


@dataclass(frozen=True)
class DetailPresentation:
    heading: str
    finding: str
    review: str
    temperature: str | None
    manual_inspection: str | None
    rgb_context: str | None
    thermal_context: str | None


def irradiance_text(report: InspectionReport) -> str:
    if report.irradiance is None: return "Einstrahlung: nicht dokumentiert."
    i=report.irradiance
    minimum="—" if i.minimum_w_m2 is None else f"{i.minimum_w_m2:g}"
    maximum="—" if i.maximum_w_m2 is None else f"{i.maximum_w_m2:g}"
    return f"Einstrahlung: Mittel {i.mean_w_m2:g} W/m²; Min {minimum}; Max {maximum}; Quelle: {i.source}"


def detail_presentation(detail: ModuleReportDetail) -> DetailPresentation:
    temperature=None
    if detail.thermal_measurement:
        m=detail.thermal_measurement
        delta="" if m.delta_t_c is None else f"; ΔT {m.delta_t_c:g} °C"
        temperature=f"Radiometrisch validiert: {m.temperature_c:g} °C{delta}; Quelle: {m.provider}"
    manual="Manuelle Prüfung erforderlich." if detail.manual_inspection_required else None
    finding=detail.finding_label or "Kein bestätigter Befund"
    def context(image):
        if image is None: return None
        if image.geometry_source=="full_frame": return "Vollbild – keine lokalisierte Modulgeometrie"
        if image.geometry_source=="persisted_module_polygon": return "Modulausschnitt – persistierte Modulgeometrie"
        if image.geometry_source.startswith("validated_cross_sensor:"): return "Lokalisierter Ausschnitt – validierte Sensorzuordnung"
        return f"Bildgeometrie: {image.geometry_source}"
    return DetailPresentation(f"Modul {detail.module_id}",finding,detail.review_status,temperature,manual,context(detail.rgb_image),context(detail.thermal_image))
