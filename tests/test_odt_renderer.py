from datetime import datetime, timezone
from odf.opendocument import load
from odf import teletype
from mcm_solarcheck.reporting.odt_renderer import render_odt
from mcm_solarcheck.reporting.report_model import InspectionReport, IrradianceSummary, OperatorSnapshot, ModuleReportDetail, ReportImage


def _text(path):
    doc=load(str(path)); return teletype.extractText(doc.text)


def test_odt_renderer_uses_same_report_semantics(tmp_path):
    report=InspectionReport("REP-9","P1","Customer GmbH","Solarpark",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",850,12,5,irradiance=IrradianceSummary(750,"on-site sensor",700,810),release_status="reviewed")
    target=render_odt(report,tmp_path/"report.odt")
    text=_text(target)
    assert "Aufbau unter Berücksichtigung" in text
    assert "Customer GmbH" in text and "Solarpark" in text
    assert "850" in text and "12" in text and "5" in text
    assert "Quelle: on-site sensor" in text


def test_odt_renderer_does_not_invent_irradiance(tmp_path):
    report=InspectionReport("R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,0,0)
    assert "Einstrahlung: nicht dokumentiert." in _text(render_odt(report,tmp_path/"r.odt"))


def test_odt_cover_uses_operator_snapshot(tmp_path):
    op=OperatorSnapshot("Operator GmbH","Werkstr. 1, 12345 Ort","office@example.invalid",website="https://example.invalid")
    report=InspectionReport("R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,0,0,operator=op)
    text=_text(render_odt(report,tmp_path/"operator.odt"))
    assert "Operator GmbH" in text and "Werkstr. 1, 12345 Ort" in text
    assert "office@example.invalid" in text


def test_odt_overview_image_does_not_depend_on_detail_state(tmp_path):
    from PIL import Image
    image=tmp_path/"overview.png"; Image.new("RGB",(20,20)).save(image)
    report=InspectionReport("R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,0,0,overview_rgb=ReportImage("R1",str(image),"rgb"))
    text=_text(render_odt(report,tmp_path/"overview.odt"))
    assert "RGB-Übersicht" in text


def test_odt_detail_includes_geometry_context(tmp_path):
    detail=ModuleReportDetail("M1","hotspot","confirmed",thermal_image=ReportImage("T1",str(tmp_path/"missing.png"),"thermal","persisted_module_polygon"))
    report=InspectionReport("R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,1,0,details=(detail,))
    text=_text(render_odt(report,tmp_path/"detail.odt"))
    assert "Modulausschnitt – persistierte Modulgeometrie" in text


def test_odt_renderer_preserves_customer_and_order_references(tmp_path):
    report=InspectionReport("R","P","Customer GmbH","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,0,0,customer_contact="Max Muster",customer_address="Kundenweg 2",customer_email="kunde@example.invalid",customer_phone="+49 555",customer_reference="K-17",order_reference="A-42")
    text=_text(render_odt(report,tmp_path/"references.odt"))
    for value in ("Max Muster","Kundenweg 2","kunde@example.invalid","+49 555","K-17","A-42"):
        assert value in text
