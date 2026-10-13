from datetime import datetime, timezone
from PIL import Image as PILImage
import pytest

from mcm_solarcheck.reporting.report_model import InspectionReport, ModuleReportDetail, ReportImage
from mcm_solarcheck.services.pv_pilot_inspection_adapter import from_reviewed_inspection
from mcm_solarcheck.services.pv_pilot_pdf_evidence import local_pilot_evidence
from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf


def _report(tmp_path, status="reviewed"):
    rgb = tmp_path / "rgb.png"
    thermal = tmp_path / "thermal.png"
    PILImage.new("RGB", (64, 48), (50, 80, 110)).save(rgb)
    PILImage.new("RGB", (64, 48), (110, 80, 50)).save(thermal)
    return InspectionReport(
        report_id="R1", project_id="P1", customer_name="Demo",
        site_name="Anlage", inspection_started_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        inspector="Expert", total_modules=1, conspicuous_modules=1,
        manual_review_modules=0, release_status=status,
        details=(ModuleReportDetail(
            "M01", "Thermische Auffälligkeit", "confirmed",
            rgb_image=ReportImage("V001", str(rgb), "rgb"),
            thermal_image=ReportImage("T001", str(thermal), "thermal"),
        ),),
    )


def test_pdf_embeds_reviewed_rgb_thermal(tmp_path):
    inspection = _report(tmp_path)
    pilot = from_reviewed_inspection(inspection, limitations="Keine Celsiusvalidierung")
    evidence = local_pilot_evidence(inspection)
    destination = tmp_path / "report.pdf"
    export_pilot_pdf(pilot, destination, evidence=evidence)
    assert destination.read_bytes().startswith(b"%PDF")
    assert destination.stat().st_size > 1000


def test_draft_evidence_rejected(tmp_path):
    with pytest.raises(PermissionError):
        local_pilot_evidence(_report(tmp_path, "draft"))


def test_missing_evidence_fails_closed(tmp_path):
    inspection = _report(tmp_path)
    (tmp_path / "rgb.png").unlink()
    with pytest.raises(FileNotFoundError):
        local_pilot_evidence(inspection)


def test_unmatched_module_rejected(tmp_path):
    from dataclasses import replace
    inspection = _report(tmp_path)
    pilot = from_reviewed_inspection(inspection, limitations="Grenzen")
    evidence = replace(local_pilot_evidence(inspection)[0], module="M02")
    with pytest.raises(ValueError):
        export_pilot_pdf(pilot, tmp_path / "out.pdf", evidence=(evidence,))
