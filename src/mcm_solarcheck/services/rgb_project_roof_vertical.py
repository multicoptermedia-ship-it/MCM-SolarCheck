"""Whole imported DJI RGB project -> bounded locally surveyed roof tiles.

Independent EXTERNAL camera poses/roof controls are mandatory; no automatic SfM,
metric orthophoto verification, thermal registration or PV-module identification.
Reads each original once, strictly read-only; no external network or ODM backend.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3

import cv2
import numpy as np

from mcm_solarcheck.domain.models import ImageFrame, Pose
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D,
)
from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid
from mcm_solarcheck.services.rgb_roof_control_point_gate import (
    RGBRoofHeldOutControl, check_held_out_rgb_roof_controls,
)
from mcm_solarcheck.services.rgb_surface_tile_mosaic import RGBMosaicSource
from mcm_solarcheck.services.rgb_surface_tile_render import render_rgb_surface_tile
from mcm_solarcheck.services.rgb_surface_tiles import plan_rgb_surface_tiles

_RGB = re.compile(r"DJI_\d{14}_\d{4}_V\.JPG\Z", re.IGNORECASE)


class RGBProjectRoofCancelled(RuntimeError):
    """No diagnostic artefact may survive cooperative cancellation."""


@dataclass(frozen=True)
class RGBProjectRoofResult:
    tile_count: int
    source_count: int
    coverage_fraction: float
    overlapping_observations: int
    maximum_control_error_m: float
    manifest_path: Path
    status: str = "unverified_local_surveyed_plane_rgb_tiles"
    orthophoto_verified: bool = False
    georeferencing_verified: bool = False


def _check_cancel(should_cancel):
    if should_cancel is not None and should_cancel():
        raise RGBProjectRoofCancelled("RGB roof processing cancelled")


def _project_rgb_frames(database, project_id, *, max_frames):
    path = Path(database)
    if (not path.is_file() or path.is_symlink() or
            not isinstance(project_id, str) or not project_id.strip()):
        raise ValueError("existing regular SQLite database and project required")
    if type(max_frames) is not int or not 2 <= max_frames <= 1000:
        raise ValueError("frame budget must be between 2 and 1000")
    with closing(sqlite3.connect(path.resolve(strict=True).as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("SELECT 1 FROM projects WHERE project_id=?", (project_id,)).fetchone() is None:
            raise ValueError("selected project does not exist")
        rows = db.execute(
            "SELECT frame_id, source_file, width, height FROM image_frames WHERE project_id=?",
            (project_id,),
        ).fetchall()
    originals = []
    for identifier, filename, width, height in rows:
        if not isinstance(filename, str) or _RGB.fullmatch(Path(filename).name) is None:
            continue
        if (not isinstance(identifier, str) or not identifier or
                type(width) is not int or type(height) is not int or
                width < 128 or height < 128):
            raise ValueError("invalid imported RGB frame identity/dimensions")
        source = Path(filename)
        if not source.is_absolute():
            source = path.parent / source
        if not source.is_file() or source.is_symlink():
            raise ValueError("imported RGB originals must be regular existing files")
        originals.append((identifier, source, width, height))
    if not 2 <= len(originals) <= max_frames:
        raise ValueError("whole-project RGB frame count outside budget")
    if len({r[0] for r in originals}) != len(originals) or len({
        r[1].name.lower() for r in originals
    }) != len(originals):
        raise ValueError("ambiguous imported RGB identity")
    return tuple(sorted(originals, key=lambda f: f[1].name.lower()))


def _read_package(package):
    if not isinstance(package, dict) or package.get("schema") != "mcm.rgb_roof_external_geometry.v1":
        raise ValueError("explicit external camera and roof geometry package required")
    try:
        p = package["plane"]
        plane = SurveyedPlane3D(tuple(p["point_enu_m"]), tuple(p["normal_enu"]))
        g = package["grid"]
        plan = plan_rgb_surface_tiles(
            ModuleSurfaceGrid(g["u_min_m"], g["v_min_m"], g["metres_per_pixel"],
                              g["width"], g["height"]),
            tile_side_px=g["tile_side_px"], max_total_pixels=12_000_000, max_tiles=64,
        )
        configs = package["frames"]
        controls_data = package["controls"]
        provenance = package["control_survey_provenance"]
        tolerance = package["allowed_surface_error_m"]
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ValueError("incomplete external roof geometry package") from error
    if not isinstance(configs, list) or not isinstance(controls_data, list):
        raise ValueError("explicit frame geometry and control lists required")
    controls = []
    for item in controls_data:
        try:
            controls.append(RGBRoofHeldOutControl(
                item["frame_id"], item["control_id"],
                tuple(item["undistorted_pixel_xy"]),
                tuple(item["surveyed_point_enu_m"]),
            ))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("invalid external held-out control") from error
    return plane, plan, configs, tuple(controls), provenance, tolerance


def _build_source(record, config):
    identifier, path, width, height = record
    if not isinstance(config, dict) or config.get("frame_id") != identifier:
        raise ValueError("external geometry must match every imported RGB frame")
    try:
        pose = Pose(**config["imported_pose_degrees"])
        frame = ImageFrame(identifier, path, width=width, height=height, camera_pose=pose)
        k = config["intrinsics"]
        intrinsics = PinholeIntrinsics(k["fx"], k["fy"], k["cx"], k["cy"])
        geometry = VerifiedCameraGeometry(
            intrinsics,
            CameraExtrinsicsENU(
                tuple(config["center_enu_m"]),
                tuple(tuple(row) for row in config["camera_to_enu"]),
            ),
            width, height,
            config["calibration_provenance"], config["rotation_provenance"],
            config["survey_provenance"], config["lens_undistortion_verified"],
            config["reference_frames_verified"],
        )
        distortion = np.asarray(config["distortion_coefficients"], dtype=np.float64)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ValueError("missing per-frame calibrated camera evidence") from error
    if distortion.shape not in ((4,), (5,), (8,), (12,), (14,)) or not np.isfinite(distortion).all():
        raise ValueError("explicit finite calibrated lens distortion required")
    # No image buffers allocated for geometry/control checking.
    return RGBMosaicSource(frame, np.empty((0, 0, 3), dtype=np.uint8), geometry), distortion


def create_project_rgb_roof_tiles(
    database, project_id, geometry_package, output_directory, *,
    max_frames=1000, max_source_bytes=80_000_000,
    should_cancel=None, on_progress=None,
) -> RGBProjectRoofResult:
    """Use every imported RGB frame; reject absent independent survey evidence.

    This produces *diagnostic* local surface RGB PNG tiles and validity masks,
    NOT an orthophoto/GeoTIFF. The input package is externally generated:
    its stated provenance is not independently authenticated here.
    """
    _check_cancel(should_cancel)
    if type(max_source_bytes) is not int or not 1 <= max_source_bytes <= 200_000_000:
        raise ValueError("bounded source image byte limit required")
    frames = _project_rgb_frames(database, project_id, max_frames=max_frames)
    plane, plan, configs, controls, survey_provenance, tolerance = _read_package(geometry_package)
    if (len(configs) != len(frames) or
            len({c.get("frame_id") for c in configs if isinstance(c, dict)}) != len(frames)):
        raise ValueError("every imported RGB frame requires unique camera geometry")
    lookup = {c["frame_id"]: c for c in configs}
    built = tuple(_build_source(record, lookup.get(record[0])) for record in frames)
    sources = tuple(row[0] for row in built)
    audit = check_held_out_rgb_roof_controls(
        sources, plane, controls,
        allowed_surface_error_m=tolerance,
        control_survey_provenance=survey_provenance,
    )
    _check_cancel(should_cancel)
    target = Path(output_directory)
    if not target.is_dir() or target.is_symlink() or any(target.iterdir()):
        raise ValueError("existing empty regular local output folder required")
    destination = target.resolve(strict=True)
    database_resolved = Path(database).resolve(strict=True)
    if destination == database_resolved.parent or destination in database_resolved.parents:
        raise ValueError("cannot use database folder or ancestor as output")
    for _, path, _, _ in frames:
        source = path.resolve(strict=True)
        if (destination == source.parent or destination in source.parents or
                source.parent in destination.parents):
            raise ValueError("output cannot overlap original-photo directory")
        if path.stat().st_size > max_source_bytes:
            raise ValueError("RGB source exceeds bounded byte budget")

    # Bounded memory: all *output* tiles but only one source photograph at a time.
    mosaics = [np.zeros((t.grid.height, t.grid.width, 3), np.uint8) for t in plan.tiles]
    masks = [np.zeros((t.grid.height, t.grid.width), bool) for t in plan.tiles]
    overlap = 0
    for index, (record, (evidence, distortion)) in enumerate(zip(frames, built)):
        _check_cancel(should_cancel)
        _, path, width, height = record
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None or image.shape != (height, width, 3) or image.dtype != np.uint8:
            raise ValueError("cannot decode expected primary RGB frame")
        k = evidence.geometry.intrinsics
        camera_matrix = np.array([[k.fx, 0, k.cx], [0, k.fy, k.cy], [0, 0, 1]], np.float64)
        undistorted = cv2.undistort(image, camera_matrix, distortion, None, camera_matrix)
        for tile_index, tile in enumerate(plan.tiles):
            _check_cancel(should_cancel)
            rendered = render_rgb_surface_tile(
                evidence.frame, undistorted, evidence.geometry, plane, tile,
            )
            valid = rendered.valid_mask
            mask = masks[tile_index]
            overlap += int(np.count_nonzero(mask & valid))
            fresh = valid & ~mask
            mosaics[tile_index][fresh] = rendered.bgr[fresh]
            mask |= valid
        if on_progress is not None:
            on_progress(index + 1, len(frames))
    _check_cancel(should_cancel)
    total = plan.width * plan.height
    covered = sum(int(m.sum()) for m in masks)
    published = []
    try:
        for tile, raster, mask in zip(plan.tiles, mosaics, masks):
            _check_cancel(should_cancel)
            prefix = f"rgb-roof-r{tile.row:03d}-c{tile.column:03d}"
            png = target / (prefix + ".png")
            valid_png = target / (prefix + "-valid.png")
            if not cv2.imwrite(str(png), raster):
                raise OSError("cannot write local RGB tile")
            published.append(png)
            if not cv2.imwrite(str(valid_png), mask.astype(np.uint8) * 255):
                raise OSError("cannot write local validity mask")
            published.append(valid_png)
        _check_cancel(should_cancel)
        manifest = target / "rgb-roof-project-diagnostic.json"
        summary = {
            "schema": "mcm.rgb_roof_project_diagnostic.v1",
            "status": "unverified_local_surveyed_plane_rgb_tiles",
            "whole_imported_rgb_series_processed": True,
            "source_count": len(frames), "tile_count": len(plan.tiles),
            "covered_fraction": covered / total, "missing_surface_pixels": total - covered,
            "overlapping_observations": overlap,
            "held_out_control_count": audit.checked_control_count,
            "maximum_control_error_m": audit.maximum_surface_error_m,
            "p95_control_error_m": audit.p95_surface_error_m,
            "controls_provenance_independently_authenticated": False,
            "rgb_orthophoto_verified": False, "georeferencing_verified": False,
            "pv_module_detection_performed": False,
            "thermal_registration_verified": False,
        }
        with manifest.open("x", encoding="utf-8") as stream:
            published.append(manifest)
            json.dump(summary, stream, indent=2, sort_keys=True)
            stream.write("\n")
        _check_cancel(should_cancel)
    except BaseException:
        for path in reversed(published):
            path.unlink(missing_ok=True)
        raise
    return RGBProjectRoofResult(
        len(plan.tiles), len(frames), covered / total, overlap,
        audit.maximum_surface_error_m, manifest,
    )
