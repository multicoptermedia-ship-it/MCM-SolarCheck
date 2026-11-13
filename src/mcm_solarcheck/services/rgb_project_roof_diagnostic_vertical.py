"""Candidate-only whole-project RGB roof diagnostic after independent holdouts.

Reuses the SAME inverse plane pixel sampler as verified rectification, but
never calls VerifiedCameraGeometry nor fabricates its verified flags.
Project-wide candidate roof images are ALWAYS UNVERIFIED visual diagnostics;
no metric/georeferencing/module/thermal permission is derived from them.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import cv2
import numpy as np

from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D,
)
from mcm_solarcheck.services.module_plane_rectification import (
    ModuleSurfaceGrid, sample_unverified_surface_candidate,
)
from mcm_solarcheck.services.rgb_surface_tiles import plan_rgb_surface_tiles
from mcm_solarcheck.services.rgb_project_roof_vertical import _project_rgb_frames
from mcm_solarcheck.services.rgb_project_roof_evidence_gate import (
    screen_project_rgb_roof_geometry,
)


class RGBDiagnosticRoofCancelled(RuntimeError):
    """Cooperative cancellation cannot publish a partial diagnostic flight."""


@dataclass(frozen=True)
class RGBUnverifiedRoofTilesResult:
    rgb_frame_count: int
    tile_count: int
    covered_fraction: float
    rooftop_holdouts_checked: int
    overlap_pixel_observations: int
    manifest_path: Path
    state: str = "unverified_whole_project_candidate_roof_tiles"
    survey_authenticity_verified: bool = False
    eligible_for_verified_roof_tiles: bool = False
    metric_scale_verified: bool = False
    orthophoto_verified: bool = False


def render_unverified_project_roof_tiles(
    database, project_id, candidate_manifest: dict, candidate_arrays: dict,
    gcp_survey: dict, roof_survey: dict, output_directory,
    *, max_frames: int = 1000, max_source_bytes: int = 80_000_000,
    should_cancel=None, on_progress=None,
) -> RGBUnverifiedRoofTilesResult:
    """One local path: ALL project RGB -> holdout gate -> candidate roof PNG/masks.

    No metric authority: even correct synthetic or real numeric observations
    cannot authenticate an independent survey or final camera calibration.
    """
    def cancel():
        if should_cancel is not None and should_cancel():
            raise RGBDiagnosticRoofCancelled("RGB diagnostic roof tiles cancelled")

    cancel()
    if (type(max_source_bytes) is not int
            or not 1 <= max_source_bytes <= 200_000_000):
        raise ValueError("bounded whole-flight RGB source byte limit required")
    # Fail closed BEFORE ANY input RGB image is decoded or file is created.
    audit = screen_project_rgb_roof_geometry(
        database, project_id, candidate_manifest, candidate_arrays,
        gcp_survey, roof_survey, max_frames=max_frames,
        should_cancel=should_cancel,
    )
    frames = _project_rgb_frames(database, project_id, max_frames=max_frames)
    if len(frames) != audit.source_count:
        raise ValueError("project RGB frame list changed since evidence screen")
    try:
        plane_description = roof_survey["plane"]
        plane = SurveyedPlane3D(
            tuple(plane_description["point_enu_m"]),
            tuple(plane_description["normal_enu"]),
        )
        grid_spec = roof_survey["grid"]
        plan = plan_rgb_surface_tiles(
            ModuleSurfaceGrid(
                grid_spec["u_min_m"], grid_spec["v_min_m"],
                grid_spec["metres_per_pixel"], grid_spec["width"],
                grid_spec["height"],
            ),
            tile_side_px=grid_spec["tile_side_px"],
            max_total_pixels=12_000_000, max_tiles=64,
        )
        calibration = roof_survey["calibration_evidence"]
        distortion = np.asarray(
            calibration["distortion_coefficients"], dtype=np.float64,
        )
        lens_reference = calibration["lens_correction_reference"]
        intrinsics = np.asarray(
            candidate_arrays["intrinsics_undistorted_pixels"], dtype=np.float64,
        )
        centers = np.asarray(
            candidate_arrays["camera_centers_enu_candidate_m"], dtype=np.float64,
        )
        rotations = np.asarray(
            candidate_arrays["camera_to_enu_candidate"], dtype=np.float64,
        )
    except (KeyError, ValueError, TypeError, OverflowError) as error:
        raise ValueError("explicit candidate camera/roof lens correction evidence required") from error
    if (distortion.shape not in ((4,), (5,), (8,), (12,), (14,))
            or not np.isfinite(distortion).all()
            or not isinstance(lens_reference, str) or not lens_reference.strip()
            or calibration.get("undistorted_pixel_coordinates") is not True):
        raise ValueError("calibrated lens correction coefficients/ref required")
    if len(plan.tiles) != audit.candidate_tile_count:
        raise ValueError("roof tile plan changed after independent evidence gate")
    k = PinholeIntrinsics(*(float(v) for v in intrinsics))
    k_matrix = np.array(
        ((k.fx, 0., k.cx), (0., k.fy, k.cy), (0., 0., 1.)),
        dtype=np.float64,
    )
    target = Path(output_directory)
    if not target.is_dir() or target.is_symlink() or any(target.iterdir()):
        raise ValueError("pre-existing empty regular diagnostic output directory required")
    dest = target.resolve(strict=True)
    db = Path(database).resolve(strict=True)
    if dest == db.parent or dest in db.parents:
        raise ValueError("diagnostic output must not contain original SQLite")
    for _, photo, _, _ in frames:
        resolved = photo.resolve(strict=True)
        if (dest == resolved.parent or dest in resolved.parents
                or resolved.parent in dest.parents
                or photo.stat().st_size > max_source_bytes):
            raise ValueError("diagnostic output overlaps images or exceeds RGB source budget")
    # Bounded RAM: only output tiles plus ONE decoded RGB photograph at a time.
    rasters = [np.zeros((tile.grid.height, tile.grid.width, 3), dtype=np.uint8)
               for tile in plan.tiles]
    masks = [np.zeros((tile.grid.height, tile.grid.width), dtype=bool)
             for tile in plan.tiles]
    overlaps = 0
    pixel_error_sum = 0.
    for i, (fid, photo, width, height) in enumerate(frames):
        cancel()
        image = cv2.imread(str(photo), cv2.IMREAD_COLOR)
        if (image is None or image.dtype != np.uint8
                or image.shape != (height, width, 3)):
            raise ValueError("cannot decode full primary RGB image with expected dimensions")
        undistorted = cv2.undistort(
            image, k_matrix, distortion, None, k_matrix,
        )
        extrinsics = CameraExtrinsicsENU(
            tuple(float(v) for v in centers[i]),
            tuple(tuple(float(v) for v in row) for row in rotations[i]),
        )
        for tile_index, tile in enumerate(plan.tiles):
            cancel()
            try:
                rendered = sample_unverified_surface_candidate(
                    undistorted, k, extrinsics, plane,
                    tile.grid, max_pixels=2048*2048,
                )
            except ValueError as error:
                if str(error) == "surface grid has no visible image coverage":
                    continue
                raise
            valid = rendered.valid_mask
            mask = masks[tile_index]
            overlap = valid & mask
            count = int(np.count_nonzero(overlap))
            if count:
                diff = np.abs(
                    rasters[tile_index][overlap].astype(np.int16) -
                    rendered.image[overlap].astype(np.int16),
                ).mean(axis=1)
                pixel_error_sum += float(np.sum(diff))
                overlaps += count
            fresh = valid & ~mask
            rasters[tile_index][fresh] = rendered.image[fresh]
            mask |= valid
        if on_progress is not None:
            on_progress(i+1,len(frames))
    cancel()
    covered = sum(int(np.count_nonzero(m)) for m in masks)
    total = plan.width * plan.height
    if covered == 0:
        raise ValueError("candidate roof surface has zero valid RGB image coverage")
    written = []
    try:
        for tile, raster, mask in zip(plan.tiles, rasters, masks):
            cancel()
            prefix = f"rgb-roof-r{tile.row:03d}-c{tile.column:03d}"
            png = target / (prefix + ".png")
            mask_file = target / (prefix + "-valid.png")
            if not cv2.imwrite(str(png), raster):
                raise OSError("cannot publish RGB diagnostic roof tile")
            written.append(png)
            if not cv2.imwrite(str(mask_file), mask.astype(np.uint8)*255):
                raise OSError("cannot publish RGB diagnostic roof validity mask")
            written.append(mask_file)
        cancel()
        manifest = target / "rgb-roof-unverified-diagnostic.json"
        metadata = {
            "schema": "mcm.rgb_candidate_roof_tiles.v1",
            "state": "unverified_whole_project_candidate_roof_tiles",
            "project_id": project_id,
            "whole_imported_rgb_series_processed": True,
            "rgb_source_count": len(frames),
            "tile_count": len(plan.tiles),
            "covered_fraction": covered/total,
            "missing_surface_pixels": total-covered,
            "independent_roof_holdout_count": audit.rooftop_holdout_count,
            "maximum_roof_holdout_error_m": audit.largest_per_camera_error_m,
            "p95_roof_holdout_error_m": audit.p95_rooftop_error_m,
            "overlap_observations": overlaps,
            "overlap_rgb_mean_absolute_difference": (
                pixel_error_sum/overlaps if overlaps else None
            ),
            "overlap_visual_review_required": True,
            "survey_authenticity_verified": False,
            "camera_calibration_independently_verified": False,
            "metric_scale_verified": False,
            "georeferencing_verified": False,
            "eligible_for_verified_roof_tiles": False,
            "orthophoto_verified": False,
            "pv_module_detection_performed": False,
            "thermal_registration_verified": False,
        }
        with manifest.open("x", encoding="utf-8") as handle:
            written.append(manifest)
            json.dump(metadata, handle, indent=2, sort_keys=True)
            handle.write("\n")
        cancel()
    except BaseException:
        for path in reversed(written):
            path.unlink(missing_ok=True)
        raise
    return RGBUnverifiedRoofTilesResult(
        len(frames),len(plan.tiles),covered/total,
        audit.rooftop_holdout_count,overlaps,manifest,
    )
