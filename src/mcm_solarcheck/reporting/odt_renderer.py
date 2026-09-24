"""Editable ODT renderer using the same neutral Phase 9 report contract as DOCX."""
from __future__ import annotations
from pathlib import Path
from odf.opendocument import OpenDocumentText
from odf.text import H, P
from odf.table import Table, TableRow, TableCell
from .docx_renderer import REPORT_STANDARD_WORDING
from .report_model import InspectionReport


def _p(parent,text): parent.addElement(P(text=str(text)))
def _row(table,label,value):
    row=TableRow()
    for item in (label,value):
        cell=TableCell(); _p(cell,item); row.addElement(cell)
    table.addElement(row)


def render_odt(report: InspectionReport, destination: str | Path) -> Path:
    """Render editable ODT without introducing renderer-specific evidence logic."""
    destination=Path(destination); doc=OpenDocumentText()
    doc.text.addElement(H(outlinelevel=1,text="MCM-SolarCheck"))
    _p(doc.text,REPORT_STANDARD_WORDING); _p(doc.text,f"Bericht: {report.report_id}")
    _p(doc.text,f"Kunde: {report.customer_name}"); _p(doc.text,f"Anlage: {report.site_name}")
    _p(doc.text,f"Standort: {report.site_address or '—'}")
    doc.text.addElement(H(outlinelevel=1,text="Übersicht"))
    table=Table(name="overview")
    for label,value in (
        ("Kunde",report.customer_name),("Anlage",report.site_name),
        ("Prüfbeginn",report.inspection_started_at.isoformat()),("Prüfer",report.inspector),
        ("PV-Module geprüft",report.total_modules),("Module mit dokumentiertem Befund",report.conspicuous_modules),
        ("Manuelle Prüfung erforderlich",report.manual_review_modules),
        ("Ohne dokumentierten Befund",report.modules_without_documented_finding),
    ): _row(table,label,value)
    doc.text.addElement(table)
    if report.irradiance:
        i=report.irradiance; _p(doc.text,f"Einstrahlung: Mittel {i.mean_w_m2:g} W/m²; Min {i.minimum_w_m2 if i.minimum_w_m2 is not None else '—'}; Max {i.maximum_w_m2 if i.maximum_w_m2 is not None else '—'}; Quelle: {i.source}")
    else: _p(doc.text,"Einstrahlung: nicht dokumentiert.")
    doc.text.addElement(H(outlinelevel=1,text="Detailbefunde"))
    if not report.details: _p(doc.text,"Keine freigegebenen Detailbefunde.")
    for detail in report.details:
        doc.text.addElement(H(outlinelevel=2,text=f"Modul {detail.module_id}"))
        _p(doc.text,f"Befund: {detail.finding_label} | Review: {detail.review_status}")
        if detail.thermal_measurement:
            m=detail.thermal_measurement; delta="" if m.delta_t_c is None else f"; ΔT {m.delta_t_c:g} °C"
            _p(doc.text,f"Radiometrisch validiert: {m.temperature_c:g} °C{delta}; Quelle: {m.provider}")
    doc.text.addElement(H(outlinelevel=1,text="Zusammenfassung und Freigabe"))
    _p(doc.text,f"Prüfer: {report.inspector}"); _p(doc.text,f"Freigabestatus: {report.release_status}")
    for item in report.equipment: _p(doc.text,f"Prüfmittel: {item.name}; ID: {item.identifier or '—'}; Kalibrierreferenz: {item.calibration_reference or '—'}")
    if report.provenance:
        _p(doc.text,f"Software: {report.provenance.software_version}"); _p(doc.text,f"Datenprovenienz: {report.provenance.evidence_statement}")
    destination.parent.mkdir(parents=True,exist_ok=True); doc.save(str(destination),addsufix=False)
    return destination
