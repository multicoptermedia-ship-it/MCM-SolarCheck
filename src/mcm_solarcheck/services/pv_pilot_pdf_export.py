"""Local customer-pilot PDF from the shared offline/online report contract."""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from mcm_solarcheck.services.pv_report_pilot_contract import PilotReport, report_sections


def export_pilot_pdf(report: PilotReport, destination: str | Path) -> Path:
    """Write a clearly labelled pilot PDF; no customer delivery or payment action."""
    if not isinstance(report, PilotReport):
        raise TypeError("PilotReport required")
    destination = Path(destination)
    if destination.suffix.lower() != ".pdf":
        raise ValueError("destination must be PDF")
    if not destination.parent.is_dir():
        raise FileNotFoundError("destination directory must already exist")
    styles = getSampleStyleSheet()
    story = []
    for index, (heading, value) in enumerate(report_sections(report)):
        story.append(Paragraph(escape(heading), styles["Title"] if index == 0 else styles["Heading2"]))
        for line in value.splitlines():
            story.append(Paragraph(escape(line), styles["BodyText"]))
        story.append(Spacer(1, 4 * mm))
    SimpleDocTemplate(str(destination), pagesize=A4, leftMargin=18 * mm,
                      rightMargin=18 * mm).build(story)
    return destination
