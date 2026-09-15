from datetime import datetime,timezone
from pathlib import Path
from mcm_solarcheck.domain.models import Finding,ThermalFrame
from mcm_solarcheck.reporting.data import InspectionReportDataService
from mcm_solarcheck.review.findings import ReviewStatus,review_finding
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade,ThermalQualityResult

def test_report_keeps_uncalibrated_confirmed_finding_explicit(tmp_path):
    db=ProjectDatabase(tmp_path/'r.sqlite');db.initialize();db.create_project('P','Plant')
    frame=ThermalFrame(frame_id='T-1',source_file=Path('T.JPG'),thermal_width=640,thermal_height=512,thermal_source='raw')
    q=ThermalQualityResult(ThermalQualityGrade.PASS,(),RawThermalStatistics(1,1000,500,500,900,990,999))
    finding=Finding('F-1','T-1',10,20,raw_value=900,temperature_c=None)
    db.save_thermal_result('P',frame,q,(finding,))
    _,audit=review_finding(finding,status=ReviewStatus.CONFIRMED,reviewer='Inspector',note='Confirmed from evidence',reviewed_at_utc=datetime(2026,1,1,tzinfo=timezone.utc));db.save_review(audit,project_id='P')
    report=InspectionReportDataService(db).build('P')
    assert report.project_name=='Plant';assert len(report.confirmed_findings)==1
    assert report.confirmed_findings[0].finding.temperature_c is None
    assert report.confirmed_findings[0].review_note=='Confirmed from evidence'
    assert report.temperature_evidence_validated is False

def test_empty_report_does_not_claim_temperature_validation(tmp_path):
    db=ProjectDatabase(tmp_path/'r.sqlite');db.initialize();db.create_project('P','Empty')
    report=InspectionReportDataService(db).build('P')
    assert report.confirmed_findings==();assert report.temperature_evidence_validated is False
