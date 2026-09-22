"""Persist conservative cross-sensor assignment evidence on Findings."""
from __future__ import annotations

from dataclasses import replace

from mcm_solarcheck.domain.models import Finding, PVModule
from mcm_solarcheck.pairing.geometry import PixelTransform
from mcm_solarcheck.vision.cross_sensor_assignment import assign_thermal_point_to_rgb_module


def link_finding_to_rgb_module(
    finding: Finding,
    *,
    rgb_frame_id: str,
    rgb_modules: tuple[PVModule, ...],
    transform: PixelTransform,
    pair_id: str | None = None,
    pair_confidence: float | None = None,
    safety_factor: float = 1.0,
) -> Finding:
    """Return a Finding enriched with auditable RGB/Thermal linkage metadata.

    A module_id is written only for an unambiguous, validated cross-sensor
    assignment.  Failed/ambiguous attempts remain visible in metadata.
    """
    if pair_confidence is not None and not 0.0 <= pair_confidence <= 1.0:
        raise ValueError("pair_confidence must be between 0 and 1")
    if finding.thermal_frame_id == rgb_frame_id:
        raise ValueError("thermal and RGB frame ids must differ")
    result = assign_thermal_point_to_rgb_module(
        thermal_x=finding.pixel_x,
        thermal_y=finding.pixel_y,
        transform=transform,
        rgb_modules=rgb_modules,
        rgb_frame_id=rgb_frame_id,
        safety_factor=safety_factor,
    )
    metadata = dict(finding.metadata)
    metadata["cross_sensor_status"] = result.status
    metadata["rgb_frame_id"] = rgb_frame_id
    metadata["transform_method"] = transform.method
    metadata["transform_validated"] = str(transform.validated).lower()
    if pair_id is not None:
        metadata["pair_id"] = pair_id
    if pair_confidence is not None:
        metadata["pair_confidence"] = f"{pair_confidence:.6f}"
    if result.rgb_point is not None:
        metadata["rgb_pixel_x"] = f"{result.rgb_point[0]:.3f}"
        metadata["rgb_pixel_y"] = f"{result.rgb_point[1]:.3f}"
    if result.transform_error_px is not None:
        metadata["transform_error_px"] = f"{result.transform_error_px:.3f}"
    if result.candidates:
        metadata["cross_sensor_candidates"] = ",".join(result.candidates)

    # Never overwrite an existing module assignment with an uncertain result.
    module_id = result.module_id if result.status == "assigned" else finding.module_id
    return replace(finding, module_id=module_id, metadata=metadata)
