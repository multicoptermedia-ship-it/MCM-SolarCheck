"""Integration check: reviewed RGB and thermal evidence remain paired."""
import pytest
from PIL import Image as PILImage

from mcm_solarcheck.services.pv_pilot_pdf_evidence import PilotEvidence
from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf
from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report


def test_numbered_finding_keeps_both_source_references(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    rgb = tmp_path / "rgb.png"
    thermal = tmp_path / "thermal.png"
    PILImage.new("RGB", (120, 70), "navy").save(rgb)
    PILImage.new("RGB", (120, 70), "maroon").save(thermal)
    evidence = (PilotEvidence(
        "M-01 (fiktiv)", rgb, thermal, "RGB-001", "THERMAL-001",
        "schematisch", "schematisch",
    ),)
    output = tmp_path / "review.pdf"
    export_pilot_pdf(fictional_pilot_report(), output, evidence=evidence)
    pages = pypdf.PdfReader(str(output)).pages
    assert "Modulanalyse" in pages[3].extract_text()
    text = "\n".join(page.extract_text() for page in pages[3:])
    assert "Befund 01" in text
    assert "RGB-001" in text
    assert "THERMAL-001" in text
    assert text.count("Fachlich geprüfte Beobachtung:") == 1
