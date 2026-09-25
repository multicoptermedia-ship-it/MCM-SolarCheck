from datetime import datetime, timezone
from pathlib import Path
from mcm_solarcheck.reporting.pdf_renderer import render_pdf
from mcm_solarcheck.reporting.report_model import InspectionReport, IrradianceSummary, ModuleReportDetail, ThermalMeasurement, OperatorSnapshot


def _report():
    detail=ModuleReportDetail("M-7","hotspot_candidate","unclear",manual_inspection_required=True,thermal_measurement=ThermalMeasurement(58.2,9.1,"validated-provider",True))
    return InspectionReport("REP-9","P1","Customer GmbH","Solarpark",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",850,12,5,site_address="Solarweg 1",irradiance=IrradianceSummary(750,"on-site sensor",700,810),details=(detail,),release_status="reviewed")


def test_pdf_renderer_creates_real_pdf(tmp_path):
    target=render_pdf(_report(),tmp_path/"report.pdf")
    data=Path(target).read_bytes()
    assert data.startswith(b"%PDF-")
    assert len(data)>1000


def test_pdf_renderer_requires_existing_banner(tmp_path):
    try:
        render_pdf(_report(),tmp_path/"report.pdf",banner_path=tmp_path/"missing.png")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing banner must fail explicitly")


def test_pdf_accepts_operator_snapshot_cover(tmp_path):
    base=_report()
    report=InspectionReport(base.report_id,base.project_id,base.customer_name,base.site_name,base.inspection_started_at,base.inspector,base.total_modules,base.conspicuous_modules,base.manual_review_modules,operator=OperatorSnapshot("Operator GmbH","Werkstr. 1, 12345 Ort","office@example.invalid"))
    data=Path(render_pdf(report,tmp_path/"operator.pdf")).read_bytes()
    assert data.startswith(b"%PDF-") and len(data)>1000


def test_pdf_renderer_preserves_customer_and_order_references(tmp_path):
    report=InspectionReport("R","P","Customer GmbH","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,0,0,customer_contact="Max Muster",customer_address="Kundenweg 2",customer_email="kunde@example.invalid",customer_phone="+49 555",customer_reference="K-17",order_reference="A-42")
    data=Path(render_pdf(report,tmp_path/"references.pdf")).read_bytes()
    for value in (b"Max Muster",b"Kundenweg 2",b"kunde@example.invalid",b"+49 555",b"K-17",b"A-42"):
        assert value in data
