"""Overview metadata and manually measured irradiance for pilot PDFs."""
from dataclasses import replace

import pytest

from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report
from mcm_solarcheck.services.pv_report_pilot_contract import report_sections


def test_fictional_overview_and_manual_measurement():
    report = fictional_pilot_report()
    sections = dict(report_sections(report))
    assert sections["Anlagenadresse"].endswith("(fiktiv)")
    assert sections["Geprüfte Module"] == "120"
    assert sections["Auffällige Module"] == "4"
    assert "850 W/m²" in sections["Einstrahlungsstärke zum Messzeitpunkt"]
    assert "manuelle Messung" in sections["Einstrahlungsstärke zum Messzeitpunkt"]


def test_missing_counts_are_not_inferred_from_findings():
    report = replace(fictional_pilot_report(), total_modules=None, conspicuous_modules=None)
    sections = dict(report_sections(report))
    assert sections["Geprüfte Module"] == "nicht erfasst"
    assert sections["Auffällige Module"] == "nicht erfasst"


@pytest.mark.parametrize("changes", [
    {"total_modules": -1},
    {"conspicuous_modules": 121},
    {"irradiance_w_m2": -1},
    {"irradiance_w_m2": float("nan")},
    {"irradiance_w_m2": float("inf")},
])
def test_invalid_overview_rejected(changes):
    with pytest.raises(ValueError):
        replace(fictional_pilot_report(), **changes)
