"""German desktop presentation for privacy-safe, stable cadence status codes.

This is a translation layer, not part of module-detection or approval logic.
The future multilingual client should translate these exact codes separately.
"""
from __future__ import annotations


CADENCE_REASON_DE = {
    "invalid_detector_configuration": "ungültige Detektoreinstellungen",
    "invalid_bgr_image": "ungeeignete Bildpixel",
    "two_grid_families_required": "zwei Rasterachsen nicht gefunden",
    "independent_image_support_required": "unabhängige Bildhinweise fehlen",
    "cadence_not_confirmed": "Rasterabstand nicht unabhängig bestätigt",
    "invalid_image_dimensions": "Bildabmessungen unplausibel",
    "invalid_minimum_iou": "ungültiger Überlappungsgrenzwert",
    "cadence_candidates_not_confirmed": "alternative Rasterabstände nicht bestätigt",
    "invalid_candidate_evidence": "Rasterbelege widersprüchlich",
    "repeated_lattice_support_required": "wiederholte Rasterbelege fehlen",
    "ambiguous_lattice_supported_cadence": "mehrere gleichwertige Rasterabstände",
    "ambiguous_lattice_supported_phase": "mehrere gleichwertige Rasterphasen",
    "resolved_candidate_not_enumerated": "Rasterlösung nicht nachvollziehbar",
    "resolved_cadence_not_supported": "Rasterabstand ohne ausreichende Bildstützung",
    "resolved_phase_invalid": "ermittelte Rasterphase ungültig",
    "resolved_phase_out_of_range": "Rasterphase außerhalb des gültigen Bereichs",
    "resolved_cadence_invalid": "ermittelter Rasterabstand ungültig",
    "invalid_cadence_axes": "Anzahl der Rasterachsen ungültig",
    "invalid_cadence_multiple": "Rasterabstand-Vielfaches ungültig",
    "invalid_cadence_spacing": "Rasterlinienabstand ungültig",
    "unresolved_cadence_phase": "Rasterphase nicht eindeutig aufgelöst",
    "invalid_resolved_phase": "aufgelöste Rasterphase ungültig",
    "no_finitely_supported_cells": "keine ausreichend gestützten Rasterflächen",
    "no_spatial_overlap": "keine ausreichende räumliche Überlappung",
    "other_quality_gate": "weitere, nicht näher klassifizierte Qualitätsprüfung",
}


def describe_cadence_rejections(
    details: tuple[tuple[str, int], ...],
) -> str:
    """Render only fixed phrases, never arbitrary detector-provided content."""
    if not details:
        return "keine Cadence-Ablehnungen"
    parts = []
    for code, count in details:
        if type(count) is not int or not 1 <= count <= 3:
            continue
        phrase = CADENCE_REASON_DE.get(
            code if type(code) is str else "",
            CADENCE_REASON_DE["other_quality_gate"],
        )
        parts.append(f"{count} Bild(er): {phrase}")
    return "; ".join(parts) if parts else "keine darstellbaren Cadence-Ablehnungen"
