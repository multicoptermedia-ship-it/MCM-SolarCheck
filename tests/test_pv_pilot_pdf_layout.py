from datetime import datetime, timezone
from pathlib import Path

from PIL import Image as PILImage

from mcm_solarcheck.services.pv_pilot_pdf_layout import evidence_pair_table, pilot_styles
from mcm_solarcheck.services.pv_pilot_pdf_evidence import PilotEvidence
from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf
from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report


def test_two_column_layout_fits_a4_content_width():
    table = evidence_pair_table([], [])
    assert sum(table._colWidths) == 168 * 72 / 25.4
    assert "PilotSmall" in pilot_styles()


def test_illustrated_pdf_has_paired_evidence(tmp_path):
    rgb = tmp_path / "rgb.png"
    thermal = tmp_path / "thermal.png"
    PILImage.new("RGB", (80, 40), "navy").save(rgb)
    PILImage.new("RGB", (80, 40), "maroon").save(thermal)
    evidence = (PilotEvidence(
        "M-01 (fiktiv)", rgb, thermal, "RGB-FRAME", "T-FRAME",
        "schematisch", "schematisch",
    ),)
    destination = tmp_path / "sample.pdf"
    export_pilot_pdf(fictional_pilot_report(), destination, evidence=evidence)
    assert destination.read_bytes().startswith(b"%PDF")
    assert destination.stat().st_size > 1500


def test_without_images_still_renders(tmp_path):
    destination = tmp_path / "text-only.pdf"
    export_pilot_pdf(fictional_pilot_report(), destination)
    assert destination.exists()
