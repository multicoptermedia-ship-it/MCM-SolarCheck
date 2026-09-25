from datetime import datetime, timezone
from odf.opendocument import load
from odf import teletype
from mcm_solarcheck.reporting.odt_renderer import render_odt
from mcm_solarcheck.reporting.report_model import InspectionReport, IrradianceSummary, OperatorSnapshot


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
