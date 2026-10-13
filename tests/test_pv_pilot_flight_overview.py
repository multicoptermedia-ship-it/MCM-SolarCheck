"""Flight overview occupies page three; module analysis starts on page four."""
import pytest

from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf
from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report
from mcm_solarcheck.services.pv_pilot_flight_overview import PilotFlightOverview, flight_overview_label
from mcm_solarcheck.services.pv_pilot_synthetic_flight import fictional_flight_overview


def test_provenance_is_explicit():
    assert "Geplanter" in flight_overview_label(PilotFlightOverview(path_kind="planned"))
    assert "Tatsächlich" in flight_overview_label(PilotFlightOverview(path_kind="recorded"))
    assert "Schematische" in flight_overview_label(PilotFlightOverview(path_kind="illustrative"))
    with pytest.raises(ValueError):
        PilotFlightOverview(path_kind="unknown")


def test_pdf_has_dedicated_flight_page(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    flight = fictional_flight_overview(tmp_path)
    destination = tmp_path / "sample.pdf"
    export_pilot_pdf(fictional_pilot_report(), destination, flight_overview=flight)
    pages = pypdf.PdfReader(str(destination)).pages
    assert len(pages) >= 4
    assert "Geprüfte Module" in pages[0].extract_text()
    assert "Prüfgrundlagen" in pages[1].extract_text()
    assert "Flugdokumentation" in pages[2].extract_text()
    assert "Schematische Flugroute" in pages[2].extract_text()
    assert "Modulanalyse" in pages[3].extract_text()


def test_missing_flight_does_not_invent_route(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    destination = tmp_path / "no-flight.pdf"
    export_pilot_pdf(fictional_pilot_report(), destination)
    pages = pypdf.PdfReader(str(destination)).pages
    assert "nicht erfasst" in pages[2].extract_text()
