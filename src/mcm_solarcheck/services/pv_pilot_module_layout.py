"""Human-readable reviewed module findings; never infer electrical diagnosis."""
from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, Spacer

from mcm_solarcheck.services.pv_pilot_pdf_layout import evidence_pair_table, caption
from mcm_solarcheck.services.pv_pilot_ai_assessment import ai_display, expert_display
from mcm_solarcheck.services.pv_pilot_ai_provenance import provenance_display


def module_heading(number: int, module: str) -> str:
    if number < 1 or not module.strip():
        raise ValueError("valid finding number and module required")
    return f"Befund {number:02d} - Modul {module}"


def module_analysis_flowables(number, finding, evidence, styles, evidence_column):
    """Keep heading, reviewed observation and side-by-side image sources together."""
    heading = Paragraph(escape(module_heading(number, finding.module)), styles["Heading2"])
    observation = Paragraph(escape("Fachlich geprüfte Beobachtung: " + finding.observation), styles["BodyText"])
    classification = Paragraph(escape(ai_display(finding.ai_assessment)), styles["BodyText"])
    assessment = Paragraph(escape(expert_display(finding.ai_assessment)), styles["BodyText"])
    provenance = [
        Paragraph(escape(line), styles["PilotSmall"])
        for line in provenance_display(
            finding.ai_assessment.provenance if finding.ai_assessment is not None else None
        )
    ]
    warning = Paragraph("Hinweis: Thermische Auffälligkeiten allein belegen keine elektrische Fehlerursache.",
                        styles["PilotSmall"])
    if evidence is None:
        return [KeepTogether([heading, observation, classification, assessment, *provenance, warning,
                              Paragraph("RGB-/Thermalbildnachweise: nicht erfasst", styles["PilotSmall"])]),
                Spacer(1, 5 * mm)]
    pair = evidence_pair_table(
        evidence_column("RGB", evidence.rgb_path, evidence.rgb_frame, evidence.rgb_geometry, styles),
        evidence_column("Thermal", evidence.thermal_path, evidence.thermal_frame, evidence.thermal_geometry, styles),
    )
    return [KeepTogether([heading, observation, classification, assessment, *provenance, pair, warning]), Spacer(1, 5 * mm)]
