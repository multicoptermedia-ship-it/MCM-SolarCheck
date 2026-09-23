from mcm_solarcheck.reporting.data import InspectionReportData, ReportFinding
from mcm_solarcheck.reporting.evidence import plan_evidence_from_record
from mcm_solarcheck.reporting.model import build_report_model
from mcm_solarcheck.storage.queries import FindingRecord, InspectionSummary


def _summary(*, confirmed=1, calibrated=0):
    return InspectionSummary('P', 1, 1, 1, 1, confirmed, 0, confirmed, 0, 0, calibrated)


def _record(*, module_id=None, temperature_c=None, temperature_status=None, temperature_provider=None):
    return FindingRecord(
        finding_id='F-1', thermal_frame_id='T-1', module_id=module_id,
        pixel_x=10, pixel_y=20, finding_type='thermal_anomaly_candidate',
        confidence=.9, raw_value=22000, raw_delta_from_median=1500.0,
        temperature_c=temperature_c, reviewer_status='confirmed',
        latitude=51.0, longitude=6.5, altitude_m=112.0,
        temperature_status=temperature_status, temperature_provider=temperature_provider,
    )


def _report(record, *, validated=False, calibrated=0):
    finding=ReportFinding(record, None, None, None, 'Checked', 'Inspector')
    return build_report_model(InspectionReportData('P', 'Plant', _summary(calibrated=calibrated), (finding,), validated))


def test_frame_gps_never_substitutes_for_physical_module_identity():
    record=_record()
    report=_report(record)
    evidence=report.evidence[0]
    image_plan=plan_evidence_from_record(record, thermal_source='T.JPG')
    assert evidence.latitude==51.0 and evidence.longitude==6.5
    assert evidence.module_id is None
    assert evidence.service_location_status=='module_unresolved'
    assert image_plan.service_location_status=='module_unresolved'
    assert any('manual localization' in warning for warning in report.warnings)


def test_unproven_numeric_celsius_never_promotes_review_priority():
    record=_record(module_id='M-0042', temperature_c=55.0)
    evidence=_report(record, calibrated=1).evidence[0]
    assert evidence.service_location_status=='module_resolved'
    assert evidence.priority_level=='unrated'
    assert evidence.priority_score is None
    assert evidence.priority_reason=='temperature_provenance_required'


def test_explicit_calibration_provenance_allows_review_ordering_without_severity():
    record=_record(
        module_id='M-0042', temperature_c=55.0,
        temperature_status='calibrated', temperature_provider='reference',
    )
    report=_report(record, validated=True, calibrated=1)
    evidence=report.evidence[0]
    assert evidence.service_location_status=='module_resolved'
    assert evidence.priority_level=='review'
    assert evidence.priority_score==.9
    assert evidence.priority_reason=='calibrated_evidence_available'
    assert 'severity' not in evidence.priority_reason.lower()
    assert report.warnings==()
