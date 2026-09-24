"""Editable ODT renderer using the same neutral Phase 9 report contract as DOCX."""
from __future__ import annotations
from pathlib import Path
from odf.opendocument import OpenDocumentText
from odf.text import H, P
from odf.table import Table, TableRow, TableCell
from .docx_renderer import REPORT_STANDARD_WORDING
from .report_model import InspectionReport
from .presentation import detail_presentation, irradiance_text


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
    _p(doc.text,irradiance_text(report))
    doc.text.addElement(H(outlinelevel=1,text="Detailbefunde"))
    if not report.details: _p(doc.text,"Keine freigegebenen Detailbefunde.")
    for detail in report.details:
        view=detail_presentation(detail)
        doc.text.addElement(H(outlinelevel=2,text=view.heading))
        _p(doc.text,f"Befund: {view.finding} | Review: {view.review}")
        if view.temperature: _p(doc.text,view.temperature)
        if view.manual_inspection: _p(doc.text,view.manual_inspection)
    doc.text.addElement(H(outlinelevel=1,text="Zusammenfassung und Freigabe"))
    _p(doc.text,f"Prüfer: {report.inspector}"); _p(doc.text,f"Freigabestatus: {report.release_status}")
    for item in report.equipment: _p(doc.text,f"Prüfmittel: {item.name}; ID: {item.identifier or '—'}; Kalibrierreferenz: {item.calibration_reference or '—'}")
    if report.provenance:
        _p(doc.text,f"Software: {report.provenance.software_version}"); _p(doc.text,f"Datenprovenienz: {report.provenance.evidence_statement}")
    destination.parent.mkdir(parents=True,exist_ok=True); doc.save(str(destination),addsuffix=False)
    return destination
