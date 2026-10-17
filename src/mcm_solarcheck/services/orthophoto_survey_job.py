"""Explicit surveyed-planar orthophoto job manifest; never infer survey controls."""
from __future__ import annotations

import json
import math
from pathlib import Path

from mcm_solarcheck.services.orthomosaic_geotiff_contract import (
    GeoTIFFSpatialReference, require_geotiff_export_target,
)
from mcm_solarcheck.services.orthophoto_imported_frames import ImportedSurveyedControl


def load_surveyed_orthophoto_job(path: str | Path):
    """Read a local, explicitly confirmed survey job; no implicit calibration."""
    source = Path(path)
    if not source.is_file() or source.is_symlink() or source.suffix.lower() != ".json":
        raise ValueError("existing local JSON survey job required")
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"rgb", "thermal", "planar_surface_verified"}:
        raise ValueError("survey job requires RGB, thermal and surface verification")
    if data["planar_surface_verified"] is not True:
        raise ValueError("independently verified planar surface required")

    def layer(name):
        item = data[name]
        if not isinstance(item, dict) or set(item) != {"controls", "reference", "destination"}:
            raise ValueError(f"{name} requires controls, reference and destination")
        ref = item["reference"]
        if not isinstance(ref, dict) or set(ref) != {"crs", "transform", "width", "height"}:
            raise ValueError("explicit surveyed output grid required")
        reference = GeoTIFFSpatialReference(
            ref["crs"], tuple(ref["transform"]), ref["width"], ref["height"]
        )
        destination = Path(item["destination"])
        if not destination.is_absolute():
            destination = source.parent / destination
        require_geotiff_export_target(destination, reference)
        controls = []
        seen_ids = set()
        if not isinstance(item["controls"], list) or not item["controls"]:
            raise ValueError("at least one surveyed frame control required")
        for entry in item["controls"]:
            if not isinstance(entry, dict) or set(entry) != {"frame_id", "pixel_points", "world_points", "independently_surveyed"}:
                raise ValueError("explicit paired control points required")
            if entry["independently_surveyed"] is not True:
                raise ValueError("independently surveyed controls required")
            if not isinstance(entry["frame_id"], str) or not entry["frame_id"].strip() or entry["frame_id"] in seen_ids:
                raise ValueError("unique nonempty frame_id required")
            seen_ids.add(entry["frame_id"])
            pixel_points = entry["pixel_points"]
            world_points = entry["world_points"]
            if not isinstance(pixel_points, list) or not isinstance(world_points, list) or len(pixel_points) < 4 or len(pixel_points) != len(world_points):
                raise ValueError("at least four paired survey controls required")
            for point in pixel_points + world_points:
                if not isinstance(point, list) or len(point) != 2 or any(type(value) not in (int, float) or not math.isfinite(value) for value in point):
                    raise ValueError("survey coordinates must be finite numeric pairs")
            controls.append(ImportedSurveyedControl(
                entry["frame_id"],
                tuple(tuple(pair) for pair in entry["pixel_points"]),
                tuple(tuple(pair) for pair in entry["world_points"]),
                True,
            ))
        return tuple(controls), reference, destination

    rgb_controls, rgb_ref, rgb_target = layer("rgb")
    thermal_controls, thermal_ref, thermal_target = layer("thermal")
    if rgb_target.resolve() == thermal_target.resolve():
        raise ValueError("RGB and thermal destinations must differ")
    return rgb_controls, thermal_controls, rgb_ref, thermal_ref, rgb_target, thermal_target
