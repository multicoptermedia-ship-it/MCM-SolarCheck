from datetime import datetime, timezone
import pytest

from mcm_solarcheck.reporting.report_model import (
    InspectionReport, ModuleReportDetail, ReportImage, IrradianceSummary,
)
from mcm_solarcheck.services.pv_pilot_inspection_adapter import from_reviewed_inspection
from mcm_solarcheck.services.pv_pilot_evidence_index import evidence_index


def _inspection(status="reviewed"):
    return InspectionReport(
        report_id="R1", project_id="P1", customer_name="Demo",
        site_name="PV-Anlage", inspection_started_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        inspector="Expert", total_modules=10, conspicuous_modules=1,
        manual_review_modules=0, release_status=status,
        details=(ModuleReportDetail(
            module_id="M01", finding_label="Thermische Auffälligkeit",
            review_status="confirmed",
            rgb_image=ReportImage("V001", "/local/rgb.jpg", "rgb"),
            thermal_image=ReportImage("T001", "/local/thermal.jpg", "thermal"),
        ),),
        irradiance=IrradianceSummary(650, "Messprotokoll"),
    )


def test_reviewed_inspection_maps_to_pilot():
    pilot = from_reviewed_inspection(_inspection(), limitations="Keine validierten Celsiuswerte")
    assert pilot.findings[0].module == "M01"
    assert "650" in pilot.conditions
    assert "Keine validierten" in pilot.limitations


def test_draft_is_rejected():
    with pytest.raises(PermissionError):
        from_reviewed_inspection(_inspection("draft"), limitations="Grenzen")
    with pytest.raises(PermissionError):
        evidence_index(_inspection("draft"))


def test_evidence_index_preserves_frame_references():
    items = evidence_index(_inspection())
    assert items[0].rgb_frame == "V001"
    assert items[0].thermal_frame == "T001"
    assert items[0].rgb_geometry == "full_frame"
