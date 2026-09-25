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


def test_export_boundary_rejects_missing_format_and_extension(tmp_path):
    with pytest.raises(ValueError,match="unsupported report format: <missing>"):
        export_report(_report(),tmp_path/"report")


@pytest.mark.parametrize("suffix",["DOCX","ODT","PDF"])
def test_export_boundary_accepts_uppercase_extension(tmp_path,suffix):
    target=export_report(_report(),tmp_path/f"report.{suffix}")
    assert target.is_file()
    assert target.suffix==f".{suffix}"


@pytest.mark.parametrize("suffix",["docx","odt","pdf"])
def test_export_boundary_accepts_explicit_uppercase_format(tmp_path,suffix):
    target=export_report(_report(),tmp_path/f"report.{suffix}",format=suffix.upper())
    assert target.is_file()


@pytest.mark.parametrize("suffix",["docx","odt","pdf"])
def test_export_boundary_creates_parent_directories(tmp_path,suffix):
    target=tmp_path/"nested"/"customer"/f"report.{suffix}"
    result=export_report(_report(),target)
    assert result==target
    assert target.is_file()


def test_export_boundary_rejects_unknown_explicit_format(tmp_path):
    with pytest.raises(ValueError,match="unsupported report format"):
        export_report(_report(),tmp_path/"report.zip",format="zip")


@pytest.mark.parametrize("suffix",["docx","odt","pdf"])
def test_export_boundary_does_not_mutate_report(tmp_path,suffix):
    report=_report()
    before=repr(report)
    export_report(report,tmp_path/f"report.{suffix}")
    assert repr(report)==before


@pytest.mark.parametrize("suffix",["docx","odt","pdf"])
def test_export_boundary_returns_exact_destination_path(tmp_path,suffix):
    target=tmp_path/"delivery"/f"customer-report.{suffix}"
    assert export_report(_report(),target)==target


def test_export_boundary_rejects_format_extension_mismatch_case_insensitively(tmp_path):
    with pytest.raises(ValueError,match="extension"):
        export_report(_report(),tmp_path/"report.PDF",format="DOCX")


@pytest.mark.parametrize("suffix",["docx","odt","pdf"])
def test_export_boundary_preserves_report_release_status(tmp_path,suffix):
    report=InspectionReport("R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,0,0,release_status="reviewed")
    target=tmp_path/f"reviewed-report.{suffix}"
    export_report(report,target)
    assert report.release_status=="reviewed"
    assert target.is_file()


@pytest.mark.parametrize("suffix",["docx","odt","pdf"])
def test_export_boundary_preserves_report_identity_fields(tmp_path,suffix):
    report=InspectionReport(
        "R","P","Customer","Site",datetime(2026,9,24,12,tzinfo=timezone.utc),"Inspector",10,0,0,
        site_address="Solarstr. 1",
        customer_reference="CUST-42",
        order_reference="ORD-99",
    )
    export_report(report,tmp_path/f"identity-report.{suffix}")
    assert report.site_address=="Solarstr. 1"
    assert report.customer_reference=="CUST-42"
    assert report.order_reference=="ORD-99"
