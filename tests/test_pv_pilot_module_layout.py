"""Module report readability and evidence provenance."""
from dataclasses import replace

import pytest

from mcm_solarcheck.services.pv_pilot_module_layout import module_heading
from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf
from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report
from mcm_solarcheck.services.pv_report_pilot_contract import PilotFinding


def test_numbered_headings():
    assert module_heading(1, "M-01") == "Befund 01 - Modul M-01"
    assert module_heading(12, "M-12") == "Befund 12 - Modul M-12"
    with pytest.raises(ValueError):
        module_heading(0, "M-01")


def test_no_evidence_does_not_invent_images(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    destination = tmp_path / "no-images.pdf"
    export_pilot_pdf(fictional_pilot_report(), destination)
    pages = pypdf.PdfReader(str(destination)).pages
    text = "\n".join(p.extract_text() for p in pages[3:])
    assert "Befund 01 - Modul M-01" in text
    assert "RGB-/Thermalbildnachweise: nicht erfasst" in text
    assert "keine elektrische Fehlerursache" in text


def test_multiple_findings_are_numbered_without_duplicate_observations(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    sample = fictional_pilot_report()
    report = replace(sample, findings=sample.findings + (
        PilotFinding("M-02 (fiktiv)", "Zweite fiktive Beobachtung.", reviewed=True),
    ))
    destination = tmp_path / "two.pdf"
    export_pilot_pdf(report, destination)
    text = "\n".join(p.extract_text() for p in pypdf.PdfReader(str(destination)).pages[3:])
    assert "Befund 01" in text and "Befund 02" in text
    assert text.count("Zweite fiktive Beobachtung.") == 1
