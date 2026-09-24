from datetime import datetime, timezone
from docx import Document
from mcm_solarcheck.reporting.docx_renderer import REPORT_STANDARD_WORDING, render_docx
from mcm_solarcheck.reporting.report_model import InspectionReport, IrradianceSummary


def test_docx_renderer_keeps_customer_report_semantics(tmp_path):
    report=InspectionReport("REP-9","P1","Customer GmbH","Solarpark",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",850,12,5,site_address="Solarweg 1, 12345 Ort",irradiance=IrradianceSummary(750,"on-site sensor",700,810),release_status="reviewed")
    target=render_docx(report,tmp_path/"report.docx")
    assert target.is_file()
    doc=Document(target)
    text="\n".join(p.text for p in doc.paragraphs)+"\n"+"\n".join(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
    assert REPORT_STANDARD_WORDING in text
    assert "Customer GmbH" in text and "Solarpark" in text
    assert "850" in text and "12" in text and "5" in text
    assert "Quelle: on-site sensor" in text
    assert "vollständig normkonform" not in text.lower()


def test_docx_renderer_does_not_invent_irradiance(tmp_path):
    report=InspectionReport("R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,0,0)
    target=render_docx(report,tmp_path/"report.docx")
    text="\n".join(p.text for p in Document(target).paragraphs)
    assert "Einstrahlung: nicht dokumentiert." in text
