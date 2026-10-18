"""Attach a non-metric projective PNG and quality JSON to a reviewed PDF."""
from __future__ import annotations

import json
from pathlib import Path

from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf
from mcm_solarcheck.services.pv_pilot_flight_overview import PilotFlightOverview
from mcm_solarcheck.services.pv_report_pilot_contract import PilotReport


def export_reviewed_pdf_with_visual_preview(report, preview_png, quality_json, destination, *, evidence=()):
    """Explicitly reviewed report with non-metric illustration; no automatic findings."""
    if not isinstance(report, PilotReport):
        raise TypeError("reviewed PilotReport required")
    png, quality, target = Path(preview_png), Path(quality_json), Path(destination)
    if png.is_symlink() or quality.is_symlink() or not png.is_file() or not quality.is_file():
        raise ValueError("existing local preview PNG and quality JSON required")
    if png.suffix.lower() != ".png" or quality.suffix.lower() != ".json":
        raise ValueError("PNG and JSON inputs required")
    if target.suffix.lower() != ".pdf" or not target.parent.is_dir() or target.exists():
        raise ValueError("destination must be a new PDF in an existing directory")
    if quality.stat().st_size > 32_768:
        raise ValueError("quality JSON exceeds limit")
    with quality.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if (type(data) is not dict or data.get("schema_version") != 1 or
            data.get("preview_only") is not True or
            data.get("metric_orthophoto_verified") is not False or
            data.get("temperature_calibrated") is not False):
        raise ValueError("not a supported non-metric visual quality record")
    note = ("Nicht metrisch verifizierte RGB-Bildvorschau; "
            "kein Orthofoto-, Flaechen- oder Temperaturmessnachweis. "
            "Qualitaetsdaten liegen separat lokal vor.")
    overview = PilotFlightOverview(image_path=png, path_kind="nonmetric_visual",
                                   source_note=note)
    return export_pilot_pdf(report, target, evidence=tuple(evidence),
                            flight_overview=overview)
