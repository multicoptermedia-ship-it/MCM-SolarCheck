from mcm_solarcheck.reporting.data import InspectionReportData,ReportFinding
from mcm_solarcheck.reporting.model import build_report_model
from mcm_solarcheck.storage.queries import FindingRecord,InspectionSummary

def summary(unreviewed=0,confirmed=1,calibrated=0):
    return InspectionSummary('P',1,1,1,0,confirmed+unreviewed,unreviewed,confirmed,0,0,calibrated)
def finding(temp=None,module_id=None,latitude=51.0,longitude=6.5,temperature_status=None,temperature_provider=None):
    return FindingRecord('F-1','T-1',module_id,10,20,'thermal_anomaly_candidate',0.9,20000,500.0,temp,'confirmed',latitude,longitude,112.0,temperature_status=temperature_status,temperature_provider=temperature_provider)

def test_report_model_never_labels_raw_value_as_celsius():
    data=InspectionReportData('P','Plant',summary(),(ReportFinding(finding(),None,None,None,'Checked','Inspector'),),False)
    report=build_report_model(data)
    assert report.evidence[0].raw_value==20000;assert report.evidence[0].temperature_c is None
    assert 'no temperature claim' in report.temperature_statement.lower();assert report.warnings

def test_report_model_marks_pending_review():
    data=InspectionReportData('P','Plant',summary(unreviewed=2),(),False)
    report=build_report_model(data)
    assert report.inspection_status=='review_incomplete';assert any('2 finding(s) remain unreviewed' in w for w in report.warnings)

def test_report_model_accepts_explicit_validated_celsius_evidence():
    data=InspectionReportData('P','Plant',summary(calibrated=1),(ReportFinding(finding(42.5,module_id='M-0042',temperature_status='calibrated',temperature_provider='reference'),'V-1',0.99,'sequence','Confirmed','Inspector'),),True)
    report=build_report_model(data)
    assert report.evidence[0].temperature_c==42.5;assert report.warnings==();assert 'validated celsius' in report.temperature_statement.lower()


def test_report_model_uses_module_as_primary_service_location():
    data=InspectionReportData('P','Plant',summary(),(ReportFinding(finding(module_id='M-0042'),None,None,None,'Checked','Inspector'),),False)
    evidence=build_report_model(data).evidence[0]
    assert evidence.module_id=='M-0042'
    assert evidence.latitude==51.0 and evidence.longitude==6.5


def test_report_model_does_not_require_gps_when_module_is_known():
    data=InspectionReportData('P','Plant',summary(),(ReportFinding(finding(module_id='M-0042',latitude=None,longitude=None),None,None,None,'Checked','Inspector'),),False)
    evidence=build_report_model(data).evidence[0]
    assert evidence.module_id=='M-0042'
    assert evidence.latitude is None and evidence.longitude is None


def test_report_model_omits_invalid_optional_gps():
    data=InspectionReportData('P','Plant',summary(),(ReportFinding(finding(module_id='M-0042',latitude=95.0,longitude=6.5),None,None,None,'Checked','Inspector'),),False)
    evidence=build_report_model(data).evidence[0]
    assert evidence.module_id=='M-0042'
    assert evidence.latitude is None and evidence.longitude is None


def test_report_evidence_carries_conservative_review_priority():
    data=InspectionReportData('P','Plant',summary(calibrated=1),(ReportFinding(finding(42.5,module_id='M-0042',temperature_status='calibrated',temperature_provider='reference'),None,None,None,'Checked','Inspector'),),True)
    evidence=build_report_model(data).evidence[0]
    assert evidence.module_id=='M-0042'
    assert evidence.priority_level=='review'
    assert evidence.priority_score==.9


def test_uncalibrated_report_evidence_stays_unrated():
    data=InspectionReportData('P','Plant',summary(),(ReportFinding(finding(module_id='M-0042'),None,None,None,'Checked','Inspector'),),False)
    evidence=build_report_model(data).evidence[0]
    assert evidence.priority_level=='unrated'
    assert evidence.priority_score is None


def test_report_orders_reviewable_evidence_before_unrated():
    high=ReportFinding(finding(50.0,module_id='M-2',temperature_status='calibrated',temperature_provider='reference'),None,None,None,'Checked','Inspector')
    low=ReportFinding(finding(module_id='M-1'),None,None,None,'Checked','Inspector')
    data=InspectionReportData('P','Plant',summary(confirmed=2,calibrated=1),(low,high),False)
    report=build_report_model(data)
    assert [item.module_id for item in report.evidence]==['M-2','M-1']


def test_report_priority_reason_is_auditable():
    data=InspectionReportData('P','Plant',summary(calibrated=1),(ReportFinding(finding(42.5,module_id='M-0042',temperature_status='calibrated',temperature_provider='reference'),None,None,None,'Checked','Inspector'),),True)
    evidence=build_report_model(data).evidence[0]
    assert evidence.priority_reason=='calibrated_evidence_available'


def test_unrated_report_explains_missing_calibration():
    data=InspectionReportData('P','Plant',summary(),(ReportFinding(finding(module_id='M-0042'),None,None,None,'Checked','Inspector'),),False)
    assert build_report_model(data).evidence[0].priority_reason=='calibrated_temperature_required'


def test_confirmed_finding_without_module_emits_localization_warning():
    data=InspectionReportData('P','Plant',summary(),(ReportFinding(finding(),None,None,None,'Checked','Inspector'),),False)
    report=build_report_model(data)
    assert any('no resolved physical module' in warning for warning in report.warnings)


def test_resolved_module_does_not_emit_localization_warning():
    data=InspectionReportData('P','Plant',summary(),(ReportFinding(finding(module_id='M-0042'),None,None,None,'Checked','Inspector'),),False)
    report=build_report_model(data)
    assert not any('no resolved physical module' in warning for warning in report.warnings)


def test_report_marks_resolved_module_as_service_location():
    data=InspectionReportData('P','Plant',summary(),(ReportFinding(finding(module_id='M-0042'),None,None,None,'Checked','Inspector'),),False)
    evidence=build_report_model(data).evidence[0]
    assert evidence.service_location_status=='module_resolved'


def test_report_marks_missing_module_as_unresolved_service_location():
    data=InspectionReportData('P','Plant',summary(),(ReportFinding(finding(),None,None,None,'Checked','Inspector'),),False)
    evidence=build_report_model(data).evidence[0]
    assert evidence.service_location_status=='module_unresolved'


def test_report_evidence_cannot_claim_resolved_without_module():
    from mcm_solarcheck.reporting.model import ReportEvidence
    evidence=ReportEvidence('F-X','candidate',None,'T-X',None,None,None,None,None,None,None,None,service_location_status='module_resolved')
    assert evidence.service_location_status=='module_unresolved'


def test_report_priority_fails_closed_for_unproven_celsius_value():
    data=InspectionReportData('P','Plant',summary(calibrated=1),(ReportFinding(finding(42.5,module_id='M-0042'),None,None,None,'Checked','Inspector'),),False)
    evidence=build_report_model(data).evidence[0]
    assert evidence.priority_level=='unrated'
    assert evidence.priority_score is None
    assert evidence.priority_reason=='temperature_provenance_required'


# Phase 9 neutral customer-report contract
from datetime import datetime, timezone
import pytest
from mcm_solarcheck.reporting.report_model import EquipmentRecord, InspectionReport, IrradianceSummary, ModuleReportDetail, ReportImage, ReportProvenance, ThermalMeasurement


def test_phase9_report_contract_carries_reviewed_summary():
    rgb=ReportImage('R1','rgb.jpg','rgb'); thermal=ReportImage('T1','thermal.jpg','thermal')
    detail=ModuleReportDetail('M-023','thermal_hotspot_candidate','confirmed',rgb,thermal)
    report=InspectionReport('REP-1','P1','Customer','Site',datetime(2026,9,24,12,tzinfo=timezone.utc),'Inspector',850,12,5,irradiance=IrradianceSummary(750,'on-site sensor',700,810),overview_rgb=rgb,overview_thermal=thermal,details=(detail,),release_status='reviewed')
    assert report.modules_without_documented_finding==838
    assert report.details[0].module_id=='M-023'


def test_phase9_customer_detail_rejects_unreviewed_ai_suggestion():
    with pytest.raises(ValueError,match='reviewed'):
        ModuleReportDetail('M1','hotspot_candidate','unreviewed')


def test_phase9_irradiance_requires_provenance():
    with pytest.raises(ValueError,match='source'):
        IrradianceSummary(700,' ')


def test_phase9_report_rejects_impossible_counts():
    with pytest.raises(ValueError,match='counts'):
        InspectionReport('R','P','C','S',datetime.now(timezone.utc),'I',10,11,1)


def test_phase9_equipment_and_provenance_are_explicit():
    equipment=EquipmentRecord("DJI M3T","SN-123","CAL-2026")
    provenance=ReportProvenance("0.9.0","Human-reviewed findings only")
    report=InspectionReport("R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,0,0,equipment=(equipment,),provenance=provenance)
    assert report.equipment[0].calibration_reference=="CAL-2026"
    assert report.provenance.evidence_statement=="Human-reviewed findings only"


def test_phase9_rejects_non_datetime_timestamp():
    with pytest.raises(ValueError,match="must be a datetime"):
        InspectionReport("R","P","Customer","Site","2026-09-24","Inspector",10,0,0)


def test_phase9_thermal_measurement_requires_validated_provenance():
    with pytest.raises(ValueError,match="validated radiometric provenance"):
        ThermalMeasurement(61.2,12.4,"raw metadata",False)
    value=ThermalMeasurement(61.2,12.4,"validated radiometric provider",True)
    assert value.delta_t_c==12.4


def test_phase9_irradiance_requires_explicit_source_and_sane_range():
    with pytest.raises(ValueError): IrradianceSummary(750,"   ")
    with pytest.raises(ValueError): IrradianceSummary(650,"sensor",700,800)


def test_unclear_manual_detail_can_omit_defect_label():
    detail=ModuleReportDetail("M-9",None,"unclear",manual_inspection_required=True)
    assert detail.finding_label is None


def test_confirmed_detail_cannot_omit_defect_label():
    with pytest.raises(ValueError,match="requires a finding label"):
        ModuleReportDetail("M-9",None,"confirmed")


def test_unclear_without_label_requires_manual_inspection():
    with pytest.raises(ValueError,match="requires manual inspection"):
        ModuleReportDetail("M-9",None,"unclear")


def test_phase9_report_rejects_naive_timestamp():
    with pytest.raises(ValueError,match="timezone-aware"):
        InspectionReport("R","P","C","S",datetime(2026,9,24,12),"I",10,0,0)


def test_phase9_report_rejects_manual_review_count_above_total():
    with pytest.raises(ValueError,match="counts"):
        InspectionReport("R","P","C","S",datetime.now(timezone.utc),"I",10,0,11)


def test_phase9_report_image_requires_known_modality():
    with pytest.raises(ValueError,match="rgb or thermal"):
        ReportImage("F1","image.png","visible")


def test_phase9_report_rejects_wrong_overview_modality():
    thermal=ReportImage("T1","thermal.png","thermal")
    with pytest.raises(ValueError,match="overview_rgb"):
        InspectionReport("R","P","C","S",datetime.now(timezone.utc),"I",10,0,0,overview_rgb=thermal)


def test_phase9_detail_rejects_wrong_image_slot_modality():
    thermal=ReportImage("T1","thermal.png","thermal")
    with pytest.raises(ValueError,match="rgb_image"):
        ModuleReportDetail("M1","hotspot","confirmed",rgb_image=thermal)


def test_phase9_thermal_measurement_rejects_non_finite_values():
    for value in (float("nan"),float("inf"),float("-inf")):
        with pytest.raises(ValueError,match="finite"):
            ThermalMeasurement(value,None,"validated provider",True)


def test_phase9_irradiance_rejects_boolean_as_numeric_value():
    with pytest.raises(ValueError,match="finite non-negative"):
        IrradianceSummary(True,"sensor")


def test_phase9_report_counts_reject_boolean_values():
    with pytest.raises(ValueError,match="non-negative integer"):
        InspectionReport("R","P","C","S",datetime.now(timezone.utc),"I",True,0,0)


def test_phase9_report_requires_timezone_aware_timestamp():
    aware=datetime(2026,9,24,12,tzinfo=timezone.utc)
    report=InspectionReport("R","P","C","S",aware,"I",1,0,0)
    assert report.inspection_started_at.utcoffset() is not None
