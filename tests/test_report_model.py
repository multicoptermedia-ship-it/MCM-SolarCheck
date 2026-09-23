from mcm_solarcheck.reporting.data import InspectionReportData,ReportFinding
from mcm_solarcheck.reporting.model import build_report_model
from mcm_solarcheck.storage.queries import FindingRecord,InspectionSummary

def summary(unreviewed=0,confirmed=1,calibrated=0):
    return InspectionSummary('P',1,1,1,0,confirmed+unreviewed,unreviewed,confirmed,0,0,calibrated)
def finding(temp=None,module_id=None,latitude=51.0,longitude=6.5):
    return FindingRecord('F-1','T-1',module_id,10,20,'thermal_anomaly_candidate',0.9,20000,500.0,temp,'confirmed',latitude,longitude,112.0)

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
    data=InspectionReportData('P','Plant',summary(calibrated=1),(ReportFinding(finding(42.5),'V-1',0.99,'sequence','Confirmed','Inspector'),),True)
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
