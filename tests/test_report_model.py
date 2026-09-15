from mcm_solarcheck.reporting.data import InspectionReportData,ReportFinding
from mcm_solarcheck.reporting.model import build_report_model
from mcm_solarcheck.storage.queries import FindingRecord,InspectionSummary

def summary(unreviewed=0,confirmed=1,calibrated=0):
    return InspectionSummary('P',1,1,1,0,confirmed+unreviewed,unreviewed,confirmed,0,0,calibrated)
def finding(temp=None):
    return FindingRecord('F-1','T-1',None,10,20,'thermal_anomaly_candidate',0.9,20000,500.0,temp,'confirmed',51.0,6.5,112.0)

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
