"""AI suggestions are explicitly separate from expert-reviewed observations."""
from dataclasses import replace

import pytest

from mcm_solarcheck.services.pv_pilot_ai_assessment import (
    PilotAIAssessment, ai_display, expert_display,
)
from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf
from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report


def test_three_ai_states():
    suspicion = PilotAIAssessment("classified_suspicion", "Bypassdiodenfehler")
    assert ai_display(suspicion) == "KI-Klassifizierung: Verdacht auf Bypassdiodenfehler"
    assert "nicht eindeutig" in ai_display(PilotAIAssessment("unassigned"))
    assert "Keine Auffälligkeit" in ai_display(PilotAIAssessment("no_anomaly"))
    assert "nicht dokumentiert" in expert_display(suspicion)


@pytest.mark.parametrize("status,cause", [
    ("classified_suspicion", None),
    ("unassigned", "Diodenfehler"),
    ("no_anomaly", "Diodenfehler"),
    ("confirmed", "Diodenfehler"),
])
def test_unsafe_ai_assessments_rejected(status, cause):
    with pytest.raises(ValueError):
        PilotAIAssessment(status, cause)


def test_pdf_keeps_ai_and_human_evaluation_separate(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    report = fictional_pilot_report()
    finding = replace(
        report.findings[0],
        ai_assessment=PilotAIAssessment(
            "classified_suspicion", "Bypassdiodenfehler",
            "Musterbewertung: elektrische Bestätigung steht aus.",
        ),
    )
    report = replace(report, findings=(finding,))
    output = tmp_path / "ai-report.pdf"
    export_pilot_pdf(report, output)
    pages = pypdf.PdfReader(str(output)).pages
    text = "\n".join(page.extract_text() for page in pages[3:])
    assert "Verdacht auf Bypassdiodenfehler" in text
    assert "Fachliche Bewertung:" in text
    assert "elektrische Bestätigung steht aus" in text
