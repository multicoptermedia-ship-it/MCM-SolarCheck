"""Independent held-out roof control gate for the existing local RGB tile pilot.

Only inputs explicitly supplied by a qualified survey/calibration process may be
used. Declaring provenance in code is NOT evidence that the survey is correct.
No camera pose, roof slope, GSD or distortion correction is inferred from DJI
EXIF, GPS, gimbal angles or homography matches. Results are nonmetric approvals:
even a successful control check does not certify an orthophoto or georeferencing.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np

from mcm_solarcheck.services.module_camera_calibration_gate import (
    require_verified_camera_geometry,
)
from mcm_solarcheck.services.module_plane_basis import (
    basis_from_surveyed_plane, plane_coordinates,
)
from mcm_solarcheck.services.module_plane_projection import (
    SurveyedPlane3D, project_pixels_to_surveyed_plane,
)
from mcm_solarcheck.services.rgb_surface_pilot_run import (
    RGBSurfacePilotRun, run_read_only_rgb_surface_pilot,
)
from mcm_solarcheck.services.rgb_surface_tile_mosaic import RGBMosaicSource
from mcm_solarcheck.services.rgb_surface_tiles import RGBSurfaceTilePlan


@dataclass(frozen=True)
class RGBRoofHeldOutControl:
    """One externally measured 3D roof point observed at an UNDISTORTED pixel.

    A control ID can occur in multiple photographs, but only once per photo.
    It must not have been used to fit the camera/plane supplied to this check.
    """

    frame_id: str
    control_id: str
    undistorted_pixel_xy: tuple[float, float]
    surveyed_point_enu_m: tuple[float, float, float]


@dataclass(frozen=True)
class RGBRoofControlAudit:
    checked_source_count: int
    checked_control_count: int
    p95_surface_error_m: float
    maximum_surface_error_m: float
    allowed_surface_error_m: float
    minimum_spatial_spread_m: float
    control_residuals_within_tolerance: bool = True
    survey_provenance_independently_verified: bool = False
    orthophoto_verified: bool = False
    georeferencing_verified: bool = False


@dataclass(frozen=True)
class RGBRoofControlledPilot:
    """Successful local diagnostic; NEVER an automatically verified orthophoto."""

    control_audit: RGBRoofControlAudit
    preview: RGBSurfacePilotRun
    status: str = "held_out_controls_consistent_local_preview_unverified"
    orthophoto_verified: bool = False
    georeferencing_verified: bool = False


def check_held_out_rgb_roof_controls(
    sources: tuple[RGBMosaicSource, ...],
    plane: SurveyedPlane3D,
    controls: tuple[RGBRoofHeldOutControl, ...],
    *,
    allowed_surface_error_m: float,
    control_survey_provenance: str,
    minimum_controls_per_source: int = 4,
    minimum_spatial_spread_m: float = 0.2,
) -> RGBRoofControlAudit:
    """Check independent ENU control residuals for EVERY involved RGB source.

    Success means the provided control observations are geometrically consistent
    with the provided camera and plane, within a DECLARED tolerance. Provenance
    cannot be authenticated by software and remains for expert approval.
    """
    if (type(sources) is not tuple or not sources or
            any(not isinstance(s, RGBMosaicSource) for s in sources)):
        raise TypeError("nonempty prepared RGB mosaic sources required")
    if not isinstance(plane, SurveyedPlane3D):
        raise TypeError("explicit surveyed roof plane required")
    if type(controls) is not tuple or not controls or any(
        not isinstance(c, RGBRoofHeldOutControl) for c in controls
    ):
        raise ValueError("independent held-out roof controls required")
    if not isinstance(control_survey_provenance, str) or not control_survey_provenance.strip():
        raise ValueError("external control survey provenance required")
    if (type(allowed_surface_error_m) not in (float, int)
            or not isfinite(allowed_surface_error_m)
            or not 0 < allowed_surface_error_m <= 2):
        raise ValueError("finite positive bounded surface tolerance required")
    if (type(minimum_spatial_spread_m) not in (float, int)
            or not isfinite(minimum_spatial_spread_m)
            or not 0 < minimum_spatial_spread_m <= 100):
        raise ValueError("finite positive spatial spread required")
    if type(minimum_controls_per_source) is not int or not 4 <= minimum_controls_per_source <= 100:
        raise ValueError("minimum four independently surveyed controls per source required")

    frame_ids = [s.frame.frame_id for s in sources]
    if any(not isinstance(v, str) or not v for v in frame_ids) or len(frame_ids) != len(set(frame_ids)):
        raise ValueError("unique imported RGB source identifiers required")
    by_frame = {fid: [] for fid in frame_ids}
    control_ids = set()
    for control in controls:
        fid, identifier = control.frame_id, control.control_id
        if fid not in by_frame or not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("held-out control refers to unknown RGB source or ID")
        key = (fid, identifier)
        if key in control_ids:
            raise ValueError("duplicate held-out control in RGB source")
        control_ids.add(key)
        by_frame[fid].append(control)

    basis = basis_from_surveyed_plane(plane)
    errors = []
    for source in sources:
        geometry = require_verified_camera_geometry(source.frame, source.geometry)
        observations = by_frame[source.frame.frame_id]
        if len(observations) < minimum_controls_per_source:
            raise ValueError("insufficient independent controls for RGB source")
        pixels = np.asarray([c.undistorted_pixel_xy for c in observations], dtype=np.float64)
        surveyed = np.asarray([c.surveyed_point_enu_m for c in observations], dtype=np.float64)
        if (pixels.shape != (len(observations), 2)
                or surveyed.shape != (len(observations), 3)
                or not np.isfinite(pixels).all() or not np.isfinite(surveyed).all()):
            raise ValueError("finite surveyed control coordinates required")
        if np.any(pixels < 0) or np.any(pixels[:, 0] >= geometry.image_width - 1) or np.any(
            pixels[:, 1] >= geometry.image_height - 1
        ):
            raise ValueError("held-out undistorted control pixel outside image")
        surveyed_uv = plane_coordinates(
            surveyed, basis, tolerance_m=float(allowed_surface_error_m),
        )
        if np.any(np.ptp(surveyed_uv, axis=0) < minimum_spatial_spread_m):
            raise ValueError("held-out controls insufficiently distributed across roof plane")
        singular = np.linalg.svd(surveyed_uv - surveyed_uv.mean(axis=0), compute_uv=False)
        if singular[0] <= 0 or singular[-1] / singular[0] < 0.05:
            raise ValueError("collinear roof controls cannot validate plane geometry")
        predicted = project_pixels_to_surveyed_plane(
            pixels, geometry.intrinsics, geometry.extrinsics, plane,
        )
        predicted_uv = plane_coordinates(predicted, basis)
        errors.extend(np.linalg.norm(predicted_uv - surveyed_uv, axis=1).tolist())

    residuals = np.asarray(errors, dtype=np.float64)
    p95, maximum = float(np.percentile(residuals, 95)), float(np.max(residuals))
    if not np.isfinite(residuals).all() or maximum > allowed_surface_error_m:
        raise ValueError("held-out roof control residual exceeds declared surface tolerance")
    return RGBRoofControlAudit(
        len(sources), len(controls), p95, maximum,
        float(allowed_surface_error_m), float(minimum_spatial_spread_m),
    )


def run_controlled_rgb_roof_pilot(
    plan: RGBSurfaceTilePlan,
    sources: tuple[RGBMosaicSource, ...],
    plane: SurveyedPlane3D,
    controls: tuple[RGBRoofHeldOutControl, ...],
    *,
    allowed_surface_error_m: float,
    control_survey_provenance: str,
    should_cancel=None,
    on_progress=None,
) -> RGBRoofControlledPilot:
    """One vertical gate: explicit geometry + controls -> existing tile pilot.

    Refuses to render any tile if an input source has inadequate, degenerate or
    inconsistent held-out controls. Uses the existing cancellable in-memory
    tile pilot afterwards. No image, control point or customer data are saved.
    """
    if should_cancel is not None and should_cancel():
        from mcm_solarcheck.services.rgb_surface_pilot_run import RGBSurfacePilotCancelled
        raise RGBSurfacePilotCancelled()
    audit = check_held_out_rgb_roof_controls(
        sources, plane, controls,
        allowed_surface_error_m=allowed_surface_error_m,
        control_survey_provenance=control_survey_provenance,
    )
    preview = run_read_only_rgb_surface_pilot(
        plan, sources, plane,
        should_cancel=should_cancel, on_progress=on_progress,
    )
    return RGBRoofControlledPilot(audit, preview)
