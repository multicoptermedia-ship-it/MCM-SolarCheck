"""Pilot status summary carries only counts and explicitly unverified flags."""
import json

import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid
from mcm_solarcheck.services.rgb_surface_tiles import plan_rgb_surface_tiles
from mcm_solarcheck.services.rgb_surface_tile_mosaic import RGBMosaicTile
from mcm_solarcheck.services.rgb_surface_mosaic_audit import audit_rgb_roof_mosaic
from mcm_solarcheck.services.rgb_surface_pilot_run import RGBSurfacePilotRun
from mcm_solarcheck.services.rgb_surface_pilot_summary import summarize_rgb_surface_pilot

PLAN = plan_rgb_surface_tiles(ModuleSurfaceGrid(0, 0, .1, 2, 2), tile_side_px=16)
TILE = PLAN.tiles[0]


def pilot(visible):
    mask = np.full((2, 2), visible, dtype=bool)
    mosaic = RGBMosaicTile(
        TILE, np.zeros((2, 2, 3), dtype=np.uint8), mask,
        1, int(visible), 0, None,
    )
    audit = audit_rgb_roof_mosaic(PLAN, (mosaic,))
    return RGBSurfacePilotRun(
        (mosaic,), audit, 1, 1,
        "local_plane_coverage_unverified" if visible
        else "partial_or_missing_coverage_unverified",
    )


@pytest.mark.parametrize("visible", [True, False])
def test_summary_is_json_safe_and_does_not_claim_orthophoto(visible):
    result = summarize_rgb_surface_pilot(pilot(visible))
    serialized = json.dumps(result, sort_keys=True)
    assert result["local_plane_mosaic_coverage_complete"] is visible
    assert result["covered_pixels"] == (4 if visible else 0)
    assert not result["georeferencing_verified"]
    assert not result["full_flight_orthophoto_verified"]
    assert not result["thermal_registration_verified"]
    assert not result["human_review_approved"]
    assert "source_file" not in serialized
    assert "coordinates" not in serialized
    assert "private-not-read" not in serialized


def test_mutated_inconsistent_pilot_fails_closed():
    from dataclasses import replace
    with pytest.raises(ValueError, match="inconsistent"):
        summarize_rgb_surface_pilot(replace(pilot(True), processed_tile_count=0))
