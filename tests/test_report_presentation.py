from mcm_solarcheck.reporting.presentation import detail_presentation, irradiance_text
from mcm_solarcheck.reporting.report_model import IrradianceSummary, InspectionReport, ModuleReportDetail, ThermalMeasurement, ReportImage
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


def test_manual_only_detail_separates_finding_from_review_instruction():
    detail=ModuleReportDetail("M-9",None,"unclear",manual_inspection_required=True)
    view=detail_presentation(detail)
    assert view.finding=="Kein bestätigter Befund"
    assert view.manual_inspection=="Manuelle Prüfung erforderlich."


def test_image_context_does_not_overstate_full_frame_as_localized_crop():
    detail=ModuleReportDetail("M-1","hotspot_candidate","confirmed",rgb_image=ReportImage("R1","rgb.jpg","rgb","full_frame"),thermal_image=ReportImage("T1","thermal.png","thermal","persisted_module_polygon"))
    view=detail_presentation(detail)
    assert view.rgb_context=="Vollbild – keine lokalisierte Modulgeometrie"
    assert view.thermal_context=="Modulausschnitt – persistierte Modulgeometrie"


def test_validated_cross_sensor_context_is_explicit():
    detail=ModuleReportDetail("M-2","hotspot_candidate","confirmed",rgb_image=ReportImage("R2","rgb.png","rgb","validated_cross_sensor:homography"))
    assert detail_presentation(detail).rgb_context=="Lokalisierter Ausschnitt – validierte Sensorzuordnung"


def test_unknown_image_geometry_is_reported_verbatim_without_claiming_validation():
    detail=ModuleReportDetail("M-3","candidate","confirmed",thermal_image=ReportImage("T3","thermal.png","thermal","legacy-import"))
    text=detail_presentation(detail).thermal_context
    assert text=="Bildgeometrie: legacy-import"
    assert "validiert" not in text.lower()


def test_temperature_without_delta_remains_explicitly_validated():
    detail=ModuleReportDetail("M-4","candidate","confirmed",thermal_measurement=ThermalMeasurement(47.3,None,"validated-provider",True))
    assert detail_presentation(detail).temperature=="Radiometrisch validiert: 47.3 °C; Quelle: validated-provider"
