"""Conservative camera and PV module-plane geometry readiness checks.

Gimbal orientation is not the incidence angle to a tilted module surface.
These diagnostics never certify a photogrammetric reconstruction.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class CameraOrientation:
    pitch_deg: float | None
    roll_deg: float | None
    yaw_deg: float | None


@dataclass(frozen=True)
class ModulePlane:
    tilt_deg: float | None
    azimuth_deg: float | None
    provenance: str = ""
    confidence: str = ""


@dataclass(frozen=True)
class GeometryReadiness:
    metadata_complete: bool
    ready_for_reconstruction: bool
    diagnostics: tuple[str, ...]


def assess_module_plane_geometry(
    camera: CameraOrientation, plane: ModulePlane
) -> GeometryReadiness:
    """Require orientation and independent plane provenance, not just gimbal pitch."""
    errors = []
    pose = (camera.pitch_deg, camera.roll_deg, camera.yaw_deg)
    if any(v is None or not isinstance(v, (int, float)) or not math.isfinite(v) for v in pose):
        errors.append("camera orientation: finite pitch, roll and yaw required")
    elif not (-90 <= camera.pitch_deg <= 90 and -180 <= camera.roll_deg <= 180 and -360 <= camera.yaw_deg <= 360):
        errors.append("camera orientation outside supported angle range")
    if plane.tilt_deg is None or not isinstance(plane.tilt_deg, (int, float)) or not math.isfinite(plane.tilt_deg) or not 0 <= plane.tilt_deg <= 90:
        errors.append("module plane: valid independently established tilt required")
    if plane.azimuth_deg is None or not isinstance(plane.azimuth_deg, (int, float)) or not math.isfinite(plane.azimuth_deg) or not 0 <= plane.azimuth_deg < 360:
        errors.append("module plane: valid independently established azimuth required")
    if not plane.provenance.strip() or not plane.confidence.strip():
        errors.append("module plane: provenance and confidence required")
    metadata_complete = not errors
    if metadata_complete:
        errors.append("camera calibration, reference frames, overlap and surveyed controls still require separate verification")
    return GeometryReadiness(metadata_complete, False, tuple(errors))
