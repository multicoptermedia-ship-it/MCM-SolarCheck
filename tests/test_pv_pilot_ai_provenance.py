"""Provenance is optional, validated and visibly not a diagnostic certainty."""
from dataclasses import replace

import pytest

from mcm_solarcheck.services.pv_pilot_ai_provenance import PilotAIProvenance, provenance_display
from mcm_solarcheck.services.pv_pilot_ai_assessment import PilotAIAssessment
from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf
from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report


@pytest.mark.parametrize("confidence", [-0.1, 1.01, float("nan"), float("inf"), True])
def test_invalid_confidence_rejected(confidence):
    with pytest.raises(ValueError):
        PilotAIProvenance("model", "v1", "local-frame", confidence)


def test_metadata_requires_source_and_valid_decision():
    with pytest.raises(ValueError):
        PilotAIProvenance("model", " ", "frame")
    with pytest.raises(ValueError):
        PilotAIProvenance("model", "v1", "frame", reviewer_decision="confirmed")
    assert "nicht Diagnosewahrscheinlichkeit" in provenance_display(
        PilotAIProvenance("model", "v1", "frame", 0.82)
    )[2]


def test_customer_pdf_excludes_internal_provenance(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    provenance = PilotAIProvenance("fictional-detector", "0.0-test", "synthetic-frame",
                                   0.82, "corrected")
    report = fictional_pilot_report()
    finding = replace(report.findings[0], ai_assessment=PilotAIAssessment(
        "unassigned", expert_assessment="Weitere Prüfung erforderlich.",
        provenance=provenance,
    ))
    report = replace(report, findings=(finding,))
    destination = tmp_path / "provenance.pdf"
    export_pilot_pdf(report, destination)
    pages = pypdf.PdfReader(str(destination)).pages
    text = "\n".join(page.extract_text() for page in pages[3:])
    assert "fictional-detector" not in text
    assert "0.0-test" not in text
    assert "synthetic-frame" not in text
    assert "82.0 %" not in text
    assert "korrigiert" not in text
    assert "Weitere Prüfung erforderlich." in text
