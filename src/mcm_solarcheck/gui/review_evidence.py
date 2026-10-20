"""Read-only expert-review evidence presentation from persisted SQLite records.

Never interpret uncalibrated raw pixels as degrees Celsius. Showing a RGB link
does not certify a surveyed geometric correspondence or defect diagnosis.
"""
from __future__ import annotations

from math import isfinite

from mcm_solarcheck.storage.queries import FindingRecord
from mcm_solarcheck.thermal.temperature_provenance import has_validated_celsius


def _number(value: int | float | None, *, decimals: int = 3) -> str:
    """Represent finite observations without fabricating missing values."""
    if value is None or isinstance(value, bool):
        return "nicht erfasst"
    try:
        if not isfinite(float(value)):
            return "nicht erfasst"
        return f"{value:.{decimals}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError, OverflowError):
        return "nicht erfasst"


def review_evidence_text(finding: FindingRecord) -> str:
    """Provide human-readable evidence, not an automatic diagnostic decision."""
    if not isinstance(finding, FindingRecord):
        raise TypeError("persisted finding record required")

    calibrated = has_validated_celsius(
        finding.temperature_c, finding.temperature_status,
        finding.temperature_provider,
    )
    temperature = (
        f"{_number(finding.temperature_c, decimals=2)} °C "
        f"(kalibriert; Quelle: {finding.temperature_provider})"
        if calibrated else "nicht belegt (Rohwerte sind keine °C)"
    )
    if finding.rgb_frame_id is None:
        rgb = "nicht belegt"
    else:
        geometry = (
            "geometrische Verknüpfung als validiert gespeichert"
            if finding.transform_validated is True
            else "geometrische Verknüpfung nicht validiert"
        )
        rgb = f"{finding.rgb_frame_id} ({geometry})"

    return "\n".join((
        f"Befund-ID: {finding.finding_id}",
        f"Thermalbild: {finding.thermal_frame_id}",
        f"Modulbeobachtung: {finding.module_id or 'nicht zugeordnet'}",
        f"Kandidatentyp: {finding.finding_type}",
        f"Thermalpixel: x={finding.pixel_x}, y={finding.pixel_y}",
        f"Algorithmische Konfidenz (keine Diagnose): {_number(finding.confidence)}",
        f"Sensorrohwert (keine °C): {_number(finding.raw_value, decimals=0)}",
        f"Rohwert-Abweichung vom Median: {_number(finding.raw_delta_from_median)}",
        f"Temperatur in °C: {temperature}",
        f"RGB-Bildbezug: {rgb}",
        "Hinweis: Bildverknüpfung und Rohwerte belegen weder Fehlerursache "
        "noch einen kalibrierten Thermografiebefund. "
        "Entscheidungen erfordern eigenständige menschliche Prüfung.",
    ))
