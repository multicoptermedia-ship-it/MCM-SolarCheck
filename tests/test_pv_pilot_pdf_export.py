import pytest

from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf
from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report
from mcm_solarcheck.services.pv_report_pilot_contract import PilotReport


def test_pilot_pdf_is_written_locally(tmp_path):
    destination = tmp_path / "musterbericht.pdf"
    result = export_pilot_pdf(fictional_pilot_report(), destination)
    assert result == destination
    assert destination.read_bytes().startswith(b"%PDF")
    assert destination.stat().st_size > 500


def test_pilot_pdf_rejects_invalid_destination(tmp_path):
    with pytest.raises(ValueError):
        export_pilot_pdf(fictional_pilot_report(), tmp_path / "sample.txt")
    with pytest.raises(FileNotFoundError):
        export_pilot_pdf(fictional_pilot_report(), tmp_path / "missing" / "sample.pdf")


def test_pilot_pdf_requires_contract(tmp_path):
    with pytest.raises(TypeError):
        export_pilot_pdf(object(), tmp_path / "sample.pdf")


def test_report_does_not_accept_unreviewed_findings():
    from mcm_solarcheck.services.pv_report_pilot_contract import PilotFinding
    with pytest.raises(PermissionError):
        PilotReport("P", "2026", "E", "Anlage", None, "Grenzen",
                    (PilotFinding("M-01", "Beispiel"),))
