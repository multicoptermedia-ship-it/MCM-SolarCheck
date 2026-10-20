"""Fail-closed, non-diagnostic formatting of stored expert evidence."""
from dataclasses import replace

import pytest

from mcm_solarcheck.gui.review_evidence import review_evidence_text
from mcm_solarcheck.storage.queries import FindingRecord


def persisted_finding(**values):
    record = FindingRecord(
        finding_id="F-01",
        thermal_frame_id="DJI-T-01",
        module_id="M1",
        pixel_x=0,
        pixel_y=15,
        finding_type="thermal_anomaly_candidate",
        confidence=0.0,
        raw_value=0,
        raw_delta_from_median=0.0,
        temperature_c=None,
        reviewer_status="unreviewed",
        latitude=None,
        longitude=None,
        altitude_m=None,
    )
    return replace(record, **values)


def test_missing_calibration_never_translates_sensor_raw_value_to_celsius():
    text = review_evidence_text(persisted_finding(
        raw_value=18732, raw_delta_from_median=1240.25, temperature_c=63.5,
        temperature_status=None, temperature_provider=None,
    ))
    assert "Befund-ID: F-01" in text
    assert "Thermalbild: DJI-T-01" in text
    assert "Modulbeobachtung: M1" in text
    assert "Thermalpixel: x=0, y=15" in text
    assert "Sensorrohwert (keine °C): 18732" in text
    assert "Rohwert-Abweichung vom Median: 1240.25" in text
    assert "Temperatur in °C: nicht belegt" in text
    assert "63.5 °C" not in text
    assert "RGB-Bildbezug: nicht belegt" in text
    assert "Algorithmische Konfidenz (keine Diagnose): 0" in text


@pytest.mark.parametrize("status,provider,value", [
    ("unvalidated", "reference", 64.2),
    ("calibrated", None, 64.2),
    ("calibrated", "reference", float("nan")),
    ("calibrated", "reference", float("inf")),
])
def test_incomplete_or_invalid_provenance_cannot_be_displayed_as_celsius(
    status, provider, value,
):
    text = review_evidence_text(persisted_finding(
        temperature_c=value, temperature_status=status,
        temperature_provider=provider,
    ))
    assert "Temperatur in °C: nicht belegt" in text
    assert "kalibriert; Quelle:" not in text


def test_validated_temperature_is_explicitly_marked_as_calibrated():
    text = review_evidence_text(persisted_finding(
        temperature_c=62.37, temperature_status="calibrated",
        temperature_provider="reference", confidence=0.9125,
    ))
    assert "Temperatur in °C: 62.37 °C (kalibriert; Quelle: reference)" in text
    assert "Algorithmische Konfidenz (keine Diagnose): 0.912" in text


def test_rgb_link_never_claims_validated_geometry_without_flag():
    link = persisted_finding(
        rgb_frame_id="DJI-V-01", transform_validated=None,
    )
    text = review_evidence_text(link)
    assert "RGB-Bildbezug: DJI-V-01" in text
    assert "geometrische Verknüpfung nicht validiert" in text
    approved = review_evidence_text(replace(link, transform_validated=True))
    assert "geometrische Verknüpfung als validiert gespeichert" in approved
    assert "keine Diagnose" in approved
    assert "Temperatur in °C: nicht belegt" in approved


def test_no_fabricated_values_for_missing_or_nonfinite_evidence():
    text = review_evidence_text(persisted_finding(
        module_id=None,
        confidence=float("nan"), raw_value=None,
        raw_delta_from_median=float("-inf"),
    ))
    assert "Modulbeobachtung: nicht zugeordnet" in text
    assert "Algorithmische Konfidenz (keine Diagnose): nicht erfasst" in text
    assert "Sensorrohwert (keine °C): nicht erfasst" in text
    assert "Rohwert-Abweichung vom Median: nicht erfasst" in text
    assert "nan" not in text.lower()
    assert "inf" not in text.lower()


def test_evidence_presentation_rejects_untrusted_object():
    with pytest.raises(TypeError, match="persisted finding"):
        review_evidence_text({"finding_id": "injected"})
