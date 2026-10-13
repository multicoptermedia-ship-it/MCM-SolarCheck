"""Human-readable reviewed module findings; never infer electrical diagnosis."""
from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, Spacer

from mcm_solarcheck.services.pv_pilot_pdf_layout import evidence_pair_table, caption
from mcm_solarcheck.services.pv_pilot_customer_view import customer_ai_lines


def module_heading(number: int, module: str) -> str:
    if number < 1 or not module.strip():
        raise ValueError("valid finding number and module required")
    return f"Befund {number:02d} - Modul {module}"


def module_analysis_flowables(number, finding, evidence, styles, evidence_column):
    """Keep heading, reviewed observation and side-by-side image sources together."""
    heading = Paragraph(escape(module_heading(number, finding.module)), styles["Heading2"])
    observation = Paragraph(escape("Fachlich geprüfte Beobachtung: " + finding.observation), styles["BodyText"])
    customer_lines = [
        Paragraph(escape(line), styles["BodyText"])
        for line in customer_ai_lines(finding.ai_assessment)
    ]
    warning = Paragraph("Hinweis: Thermische Auffälligkeiten allein belegen keine elektrische Fehlerursache.",
                        styles["PilotSmall"])
    if evidence is None:
        return [KeepTogether([heading, observation, *customer_lines, warning,
                              Paragraph("RGB-/Thermalbildnachweise: nicht erfasst", styles["PilotSmall"])]),
                Spacer(1, 5 * mm)]
    pair = evidence_pair_table(
        evidence_column("RGB", evidence.rgb_path, evidence.rgb_frame, evidence.rgb_geometry, styles),
        evidence_column("Thermal", evidence.thermal_path, evidence.thermal_frame, evidence.thermal_geometry, styles),
    )
    return [KeepTogether([heading, observation, *customer_lines, pair, warning]), Spacer(1, 5 * mm)]
