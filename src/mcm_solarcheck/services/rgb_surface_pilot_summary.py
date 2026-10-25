"""Safe small JSON-serializable metrics for the RGB roof-plane pilot.

Does not return original pixels, geocoordinates, paths, filenames, project IDs
or camera positions. A status summary cannot approve an orthophoto.
"""
from __future__ import annotations

from mcm_solarcheck.services.rgb_surface_pilot_run import RGBSurfacePilotRun


def summarize_rgb_surface_pilot(run: RGBSurfacePilotRun) -> dict[str, object]:
    if not isinstance(run, RGBSurfacePilotRun) or not run.read_only:
        raise TypeError("completed read-only RGB pilot result required")
    report = run.audit
    if report.covered_pixels < 0 or report.missing_pixels < 0:
        raise ValueError("invalid audited image coverage")
    if run.processed_tile_count != report.tile_count or not (
        0 <= report.covered_fraction <= 1
    ):
        raise ValueError("inconsistent diagnostic mosaic results")
    return {
        "schema": "mcm.rgb_local_surface_pilot.v1",
        "state": run.state,
        "rgb_source_count": run.rgb_source_count,
        "processed_tile_count": run.processed_tile_count,
        "covered_pixels": report.covered_pixels,
        "missing_pixels": report.missing_pixels,
        "coverage_fraction": report.covered_fraction,
        "overlap_observations": report.overlapping_observations,
        "local_plane_mosaic_coverage_complete": report.completed_local_plane_mosaic,
        "georeferencing_verified": False,
        "full_flight_orthophoto_verified": False,
        "thermal_registration_verified": False,
        "human_review_approved": False,
        "read_only": True,
    }
