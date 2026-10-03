from mcm_solarcheck.reporting.presentation import detail_presentation, irradiance_text, overall_result_text
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


def test_irradiance_wording_marks_missing_range_values_without_invention():
    report=InspectionReport("R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",1,0,0,irradiance=IrradianceSummary(700,"sensor"))
    text=irradiance_text(report)
    assert "Min —" in text and "Max —" in text
    assert "Quelle: sensor" in text


def test_manual_review_wording_does_not_claim_confirmed_finding():
    detail=ModuleReportDetail("M-10",None,"unclear",manual_inspection_required=True)
    view=detail_presentation(detail)
    combined=" ".join((view.finding,view.review,view.manual_inspection)).lower()
    assert "kein bestätigter befund" in combined
    assert "manuelle prüfung erforderlich" in combined
    assert "bestätigter hotspot" not in combined


def test_full_frame_context_remains_distinct_for_both_modalities():
    detail=ModuleReportDetail("M-11","candidate","confirmed",rgb_image=ReportImage("R11","rgb.jpg","rgb","full_frame"),thermal_image=ReportImage("T11","thermal.png","thermal","full_frame"))
    view=detail_presentation(detail)
    expected="Vollbild – keine lokalisierte Modulgeometrie"
    assert view.rgb_context==expected
    assert view.thermal_context==expected


def _result_report(*, release_status="released", conspicuous=0, manual_review=0):
    return InspectionReport(
        "R-CLEAN",
        "P-CLEAN",
        "Customer",
        "Site",
        datetime(2026, 9, 26, 12, tzinfo=timezone.utc),
        "Inspector",
        20,
        conspicuous,
        manual_review,
        release_status=release_status,
    )


def test_released_clean_report_states_no_defective_modules_with_scope_limit():
    text = overall_result_text(_result_report())
    assert text is not None
    assert "Gesamtergebnis: Keine defekten Module festgestellt." in text
    assert "thermografischen Auswertung" in text
    assert "untersuchten Anlagenbereich" in text
    assert "Anlage in Ordnung" not in text


def test_clean_result_is_not_claimed_before_report_release():
    assert overall_result_text(_result_report(release_status="draft")) is None


def test_clean_result_is_not_claimed_with_conspicuous_modules():
    assert overall_result_text(_result_report(conspicuous=1)) is None


def test_clean_result_is_not_claimed_with_pending_manual_review():
    assert overall_result_text(_result_report(manual_review=1)) is None
