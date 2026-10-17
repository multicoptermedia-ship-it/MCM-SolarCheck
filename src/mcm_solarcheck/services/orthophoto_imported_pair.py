"""Generate distinct native RGB and thermal GeoTIFFs from imported surveyed frames.

Limited to independently surveyed planar surfaces; not general photogrammetry.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.domain.models import ImageFrame, ThermalFrame
from mcm_solarcheck.services.orthomosaic_geotiff_contract import GeoTIFFSpatialReference, require_geotiff_export_target
from mcm_solarcheck.services.orthophoto_imported_frames import ImportedSurveyedControl, surveyed_frames_from_import
from mcm_solarcheck.services.orthophoto_planar_export import export_planar_orthophoto


@dataclass(frozen=True)
class NativeOrthophotoPair:
    rgb_geotiff: Path
    thermal_geotiff: Path


def generate_imported_planar_orthophoto_pair(
    rgb_frames: tuple[ImageFrame, ...],
    thermal_frames: tuple[ThermalFrame, ...],
    rgb_controls: tuple[ImportedSurveyedControl, ...],
    thermal_controls: tuple[ImportedSurveyedControl, ...],
    rgb_reference: GeoTIFFSpatialReference,
    thermal_reference: GeoTIFFSpatialReference,
    rgb_destination: str | Path,
    thermal_destination: str | Path,
    *,
    planar_surface_verified: bool = False,
) -> NativeOrthophotoPair:
    """Export both bands only when independent planar survey is established."""
    if planar_surface_verified is not True:
        raise ValueError("verified planar surface model required")
    rgb_target = Path(rgb_destination)
    thermal_target = Path(thermal_destination)
    if rgb_target.resolve() == thermal_target.resolve():
        raise ValueError("RGB and thermal exports require distinct destinations")
    if rgb_target.exists() or thermal_target.exists():
        raise FileExistsError("orthophoto export destination already exists")
    require_geotiff_export_target(rgb_target, rgb_reference)
    require_geotiff_export_target(thermal_target, thermal_reference)
    rgb_inputs = surveyed_frames_from_import(rgb_frames, rgb_controls)
    thermal_inputs = surveyed_frames_from_import(thermal_frames, thermal_controls, thermal=True)
    rgb_output = export_planar_orthophoto(
        rgb_inputs, rgb_target, rgb_reference, planar_surface_verified=True
    )
    try:
        thermal_output = export_planar_orthophoto(
            thermal_inputs, thermal_target, thermal_reference,
            thermal=True, planar_surface_verified=True,
        )
    except Exception:
        rgb_output.unlink(missing_ok=True)
        raise
    return NativeOrthophotoPair(rgb_output, thermal_output)
