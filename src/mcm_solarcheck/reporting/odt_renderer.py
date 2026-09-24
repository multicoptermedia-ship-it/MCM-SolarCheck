"""Editable ODT renderer using the same neutral Phase 9 report contract as DOCX."""
from __future__ import annotations
from pathlib import Path
from odf.opendocument import OpenDocumentText
from odf.text import H, P
from odf.draw import Frame, Image as OdfImage
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


def _image(doc, parent, path: str | None, label: str):
    _p(parent,label)
    if not path or not Path(path).is_file():
        _p(parent,"Bild nicht verfügbar")
        return
    href=doc.addPicture(str(path))
    frame=Frame(width="8cm",height="5.3cm",anchortype="paragraph")
    frame.addElement(OdfImage(href=href)); parent.addElement(frame)


def render_odt(report: InspectionReport, destination: str | Path, *, banner_path: str | Path | None=None) -> Path:
    """Render editable ODT without introducing renderer-specific evidence logic."""
    destination=Path(destination); doc=OpenDocumentText()
    if banner_path is not None:
        if not Path(banner_path).is_file(): raise FileNotFoundError(banner_path)
        _image(doc,doc.text,str(banner_path),"")
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
    if report.overview_rgb or report.overview_thermal:
        images=Table(name="overview-images"); row=TableRow()
        for label,item in (("RGB-Übersicht",report.overview_rgb),("Thermal-Übersicht",report.overview_thermal)):
            cell=TableCell(); _image(doc,cell,item.path if item else None,label); row.addElement(cell)
        images.addElement(row); doc.text.addElement(images)
    doc.text.addElement(H(outlinelevel=1,text="Detailbefunde"))
    if not report.details: _p(doc.text,"Keine freigegebenen Detailbefunde.")
    for detail in report.details:
        view=detail_presentation(detail)
        doc.text.addElement(H(outlinelevel=2,text=view.heading))
        _p(doc.text,f"Befund: {view.finding} | Review: {view.review}")
        if view.temperature: _p(doc.text,view.temperature)
        if view.manual_inspection: _p(doc.text,view.manual_inspection)
        images=Table(name=f"detail-{detail.module_id}"); row=TableRow()
        for label,item in (("RGB",detail.rgb_image),("Thermal",detail.thermal_image)):
            cell=TableCell(); _image(doc,cell,item.path if item else None,label); row.addElement(cell)
        images.addElement(row); doc.text.addElement(images)
    doc.text.addElement(H(outlinelevel=1,text="Zusammenfassung und Freigabe"))
    _p(doc.text,f"Prüfer: {report.inspector}"); _p(doc.text,f"Freigabestatus: {report.release_status}")
    for item in report.equipment: _p(doc.text,f"Prüfmittel: {item.name}; ID: {item.identifier or '—'}; Kalibrierreferenz: {item.calibration_reference or '—'}")
    if report.provenance:
        _p(doc.text,f"Software: {report.provenance.software_version}"); _p(doc.text,f"Datenprovenienz: {report.provenance.evidence_statement}")
    destination.parent.mkdir(parents=True,exist_ok=True); doc.save(str(destination),addsuffix=False)
    return destination
