"""A4 layout primitives shared by offline and future online pilot rendering."""
from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Table, TableStyle


def pilot_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="PilotSmall", parent=styles["BodyText"], fontSize=8,
        leading=11, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="PilotCaption", parent=styles["PilotSmall"], alignment=TA_CENTER,
        textColor=colors.HexColor("#354b60"),
    ))
    return styles


def evidence_pair_table(left, right):
    """Two equal A4-width columns with a small gap; cells are flowables."""
    table = Table([[left, right]], colWidths=[84 * mm, 84 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5df")),
    ]))
    return table


def page_decoration(canvas, doc):
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setStrokeColor(colors.HexColor("#d0dbe4"))
    canvas.line(18 * mm, height - 12 * mm, width - 18 * mm, height - 12 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#3c5367"))
    canvas.drawString(18 * mm, height - 10 * mm, "MCM-SolarCheck | Prüfbericht – Kundenmuster")
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.drawString(18 * mm, 10 * mm, "In Anlehnung an DIN IEC/TS 62446-3 – kein Normkonformitätsnachweis")
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def caption(value, styles):
    return Paragraph(escape(value), styles["PilotCaption"])
