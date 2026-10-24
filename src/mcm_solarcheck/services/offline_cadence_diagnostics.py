"""Stable, non-sensitive diagnostic codes for offline cadence feasibility checks.

Only a tightly allowlisted vocabulary may reach UI. Backend returns language-
independent codes; localized labels belong to the desktop presentation layer.
Never forward arbitrary detector exception strings, source paths or file IDs.
"""
from __future__ import annotations


KNOWN_CADENCE_REJECTION_REASONS = frozenset({
    "invalid_detector_configuration",
    "invalid_bgr_image",
    "two_grid_families_required",
    "independent_image_support_required",
    "cadence_not_confirmed",
    "invalid_image_dimensions",
    "invalid_minimum_iou",
    "cadence_candidates_not_confirmed",
    "invalid_candidate_evidence",
    "repeated_lattice_support_required",
    "ambiguous_lattice_supported_cadence",
    "ambiguous_lattice_supported_phase",
    "resolved_candidate_not_enumerated",
    "resolved_cadence_not_supported",
    "resolved_phase_invalid",
    "resolved_phase_out_of_range",
    "resolved_cadence_invalid",
    "invalid_cadence_axes",
    "invalid_cadence_multiple",
    "invalid_cadence_spacing",
    "unresolved_cadence_phase",
    "invalid_resolved_phase",
    "no_finitely_supported_cells",
    "no_spatial_overlap",
})


def safe_cadence_reason(reason: object) -> str:
    """Convert external detector reason into a bounded, public stable code."""
    if type(reason) is str and reason in KNOWN_CADENCE_REJECTION_REASONS:
        return reason
    return "other_quality_gate"
