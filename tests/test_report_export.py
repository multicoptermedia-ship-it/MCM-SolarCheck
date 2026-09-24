from datetime import datetime, timezone
import pytest
from mcm_solarcheck.reporting.export import export_report
from mcm_solarcheck.reporting.report_model import InspectionReport


def _report(): return InspectionReport("R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,0,0)

@pytest.mark.parametrize("suffix",["docx","odt","pdf"])
def test_export_boundary_creates_requested_format(tmp_path,suffix):
    target=export_report(_report(),tmp_path/f"report.{suffix}")
    assert target.is_file() and target.suffix==f".{suffix}"


def test_export_boundary_rejects_extension_mismatch(tmp_path):
    with pytest.raises(ValueError,match="extension"):
        export_report(_report(),tmp_path/"report.pdf",format="docx")


def test_all_formats_reject_missing_banner(tmp_path):
    for suffix in ("docx","odt","pdf"):
        with pytest.raises(FileNotFoundError):
            export_report(_report(),tmp_path/f"report.{suffix}",banner_path=tmp_path/"missing.png")
