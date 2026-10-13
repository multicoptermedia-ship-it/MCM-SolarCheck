"""Local customer-pilot PDF from the shared offline/online report contract."""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image, KeepTogether

from mcm_solarcheck.services.pv_report_pilot_contract import PilotReport, report_sections
from mcm_solarcheck.services.pv_pilot_pdf_evidence import PilotEvidence
from mcm_solarcheck.services.pv_pilot_pdf_layout import (
    pilot_styles, evidence_pair_table, page_decoration, caption,
)


def _evidence_image(path: Path):
    from PIL import Image as PILImage
    with PILImage.open(path) as source:
        if source.format not in {"JPEG", "PNG"}:
            raise ValueError("evidence must be JPEG or PNG")
        width, height = source.size
        if width <= 0 or height <= 0 or width * height > 40_000_000:
            raise ValueError("invalid or oversized evidence")
        source.verify()
    scale = min(76 * mm / width, 50 * mm / height)
    return Image(str(path), width=width * scale, height=height * scale)


def _evidence_column(label, path, frame, geometry, styles):
    result = [caption(label, styles)]
    if path is None:
        result.append(Paragraph("Kein Bildnachweis vorhanden", styles["PilotSmall"]))
    else:
        result.append(_evidence_image(path))
    result.append(Paragraph(escape(
        f"Quelle: {frame or 'nicht erfasst'}; Geometrie: {geometry or 'nicht erfasst'}"
    ), styles["PilotSmall"]))
    return result


def export_pilot_pdf(
    report: PilotReport, destination: str | Path, *,
    evidence: tuple[PilotEvidence, ...] = (),
) -> Path:
    """Render reviewed local pilot PDF; never upload or transmit images."""
    if not isinstance(report, PilotReport):
        raise TypeError("PilotReport required")
    destination = Path(destination)
    if destination.suffix.lower() != ".pdf":
        raise ValueError("destination must be PDF")
    if not destination.parent.is_dir():
        raise FileNotFoundError("destination directory must already exist")
    if any(not isinstance(item, PilotEvidence) for item in evidence):
        raise TypeError("PilotEvidence required")
    modules = {finding.module for finding in report.findings}
    if len({item.module for item in evidence}) != len(evidence):
        raise ValueError("duplicate evidence module")
    if any(item.module not in modules for item in evidence):
        raise ValueError("evidence module not present in reviewed findings")
    styles = pilot_styles()
    story = []
    for index, (heading, value) in enumerate(report_sections(report)):
        story.append(Paragraph(escape(heading), styles["Title"] if index == 0 else styles["Heading2"]))
        for line in value.splitlines():
            story.append(Paragraph(escape(line), styles["BodyText"]))
        story.append(Spacer(1, 4 * mm))
    if evidence:
        story.append(Paragraph("Bildnachweise (lokale Quelldateien)", styles["Heading1"]))
    findings = {finding.module: finding.observation for finding in report.findings}
    for item in evidence:
        heading = Paragraph(escape("Modul " + item.module), styles["Heading2"])
        observation = Paragraph(escape("Beobachtung: " + findings[item.module]), styles["BodyText"])
        pair = evidence_pair_table(
            _evidence_column("RGB", item.rgb_path, item.rgb_frame, item.rgb_geometry, styles),
            _evidence_column("Thermal", item.thermal_path, item.thermal_frame, item.thermal_geometry, styles),
        )
        story.append(KeepTogether([heading, observation, pair]))
        story.append(Spacer(1, 5 * mm))
    SimpleDocTemplate(
        str(destination), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=20 * mm, bottomMargin=21 * mm,
    ).build(story, onFirstPage=page_decoration, onLaterPages=page_decoration)
    return destination
