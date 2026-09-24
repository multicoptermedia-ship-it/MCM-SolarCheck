"""Final PDF renderer using the same neutral report and presentation semantics."""
from __future__ import annotations
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, PageBreak, Image
from .docx_renderer import REPORT_STANDARD_WORDING
from .presentation import detail_presentation, irradiance_text
from .report_model import InspectionReport


def _image(path: str | None, width=78*mm):
    if path and Path(path).is_file(): return Image(path,width=width,height=52*mm,kind="proportional")
    return Paragraph("Bild nicht verfügbar",getSampleStyleSheet()["BodyText"])


def render_pdf(report: InspectionReport, destination: str | Path, *, banner_path: str | Path | None=None) -> Path:
    """Render a non-editable delivery PDF without adding unsupported evidence claims."""
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    styles=getSampleStyleSheet(); story=[]
    if banner_path is not None:
        if not Path(banner_path).is_file(): raise FileNotFoundError(banner_path)
        story.append(_image(str(banner_path),170*mm))
    story += [Paragraph("MCM-SolarCheck",styles["Title"]),Paragraph(REPORT_STANDARD_WORDING,styles["BodyText"]),Spacer(1,5*mm),
              Paragraph(f"Bericht: {report.report_id}",styles["BodyText"]),Paragraph(f"Kunde: {report.customer_name}",styles["BodyText"]),
              Paragraph(f"Anlage: {report.site_name}",styles["BodyText"]),Paragraph(f"Standort: {report.site_address or '—'}",styles["BodyText"]),PageBreak(),
              Paragraph("Übersicht",styles["Heading1"])]
    rows=[
        ["Kunde",report.customer_name],["Anlage",report.site_name],["Prüfbeginn",report.inspection_started_at.isoformat()],
        ["Prüfer",report.inspector],["PV-Module geprüft",str(report.total_modules)],
        ["Module mit dokumentiertem Befund",str(report.conspicuous_modules)],["Manuelle Prüfung erforderlich",str(report.manual_review_modules)],
        ["Ohne dokumentierten Befund",str(report.modules_without_documented_finding)],
    ]
    story += [Table(rows,colWidths=[70*mm,100*mm]),Spacer(1,4*mm),Paragraph(irradiance_text(report),styles["BodyText"])]
    if report.overview_rgb or report.overview_thermal:
        story += [Spacer(1,4*mm),Table([[_image(report.overview_rgb.path if report.overview_rgb else None),_image(report.overview_thermal.path if report.overview_thermal else None)]])]
    story += [PageBreak(),Paragraph("Detailbefunde",styles["Heading1"])]
    if not report.details: story.append(Paragraph("Keine freigegebenen Detailbefunde.",styles["BodyText"]))
    for detail in report.details:
        view=detail_presentation(detail); story += [Paragraph(view.heading,styles["Heading2"]),Paragraph(f"Befund: {view.finding} | Review: {view.review}",styles["BodyText"])]
        if view.temperature: story.append(Paragraph(view.temperature,styles["BodyText"]))
        if view.manual_inspection: story.append(Paragraph(view.manual_inspection,styles["BodyText"]))
        story.append(Table([[_image(detail.rgb_image.path if detail.rgb_image else None),_image(detail.thermal_image.path if detail.thermal_image else None)]]))
    story += [PageBreak(),Paragraph("Zusammenfassung und Freigabe",styles["Heading1"]),Paragraph(f"Prüfer: {report.inspector}",styles["BodyText"]),Paragraph(f"Freigabestatus: {report.release_status}",styles["BodyText"])]
    for item in report.equipment: story.append(Paragraph(f"Prüfmittel: {item.name}; ID: {item.identifier or '—'}; Kalibrierreferenz: {item.calibration_reference or '—'}",styles["BodyText"]))
    if report.provenance:
        story += [Paragraph(f"Software: {report.provenance.software_version}",styles["BodyText"]),Paragraph(f"Datenprovenienz: {report.provenance.evidence_statement}",styles["BodyText"])]
    SimpleDocTemplate(str(destination),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=16*mm,bottomMargin=16*mm).build(story)
    return destination
