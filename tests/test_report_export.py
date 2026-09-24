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


def test_odt_banner_is_not_silently_dropped(tmp_path):
    banner=tmp_path/"banner.png"; banner.write_bytes(b"placeholder")
    with pytest.raises(ValueError,match="not implemented"):
        export_report(_report(),tmp_path/"report.odt",banner_path=banner)
