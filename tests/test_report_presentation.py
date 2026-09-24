from mcm_solarcheck.reporting.presentation import detail_presentation, irradiance_text
from mcm_solarcheck.reporting.report_model import IrradianceSummary, InspectionReport, ModuleReportDetail, ThermalMeasurement
from datetime import datetime, timezone


def test_shared_presentation_preserves_manual_review_and_validated_temperature():
    detail=ModuleReportDetail("M-7","hotspot_candidate","unclear",manual_inspection_required=True,thermal_measurement=ThermalMeasurement(58.2,9.1,"validated-provider",True))
    view=detail_presentation(detail)
    assert view.heading=="Modul M-7"
    assert view.review=="unclear"
    assert view.manual_inspection=="Manuelle Prüfung erforderlich."
    assert view.temperature=="Radiometrisch validiert: 58.2 °C; ΔT 9.1 °C; Quelle: validated-provider"


def test_shared_irradiance_wording_never_implies_measurement_without_source():
    report=InspectionReport("R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",1,0,0,irradiance=IrradianceSummary(700,"DJI metadata / derived"))
    text=irradiance_text(report)
    assert "Quelle: DJI metadata / derived" in text
    assert "gemessen" not in text.lower()
