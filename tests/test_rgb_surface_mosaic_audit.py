"""No missing or duplicate RGB mosaic tiles can masquerade as finished coverage."""
import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid
from mcm_solarcheck.services.rgb_surface_tiles import plan_rgb_surface_tiles
from mcm_solarcheck.services.rgb_surface_tile_mosaic import RGBMosaicTile
from mcm_solarcheck.services.rgb_surface_mosaic_audit import audit_rgb_roof_mosaic

PLAN = plan_rgb_surface_tiles(ModuleSurfaceGrid(0, 0, .1, 33, 16), tile_side_px=16)


def mosaic(tile, valid=True):
    g = tile.grid
    return RGBMosaicTile(
        tile, np.zeros((g.height, g.width, 3), dtype=np.uint8),
        np.full((g.height, g.width), valid, dtype=bool),
        1, int(valid), 0, None,
    )


def test_complete_local_plane_coverage_is_not_gis_orthophoto_verification():
    result = audit_rgb_roof_mosaic(PLAN, tuple(mosaic(t) for t in PLAN.tiles))
    assert result.tile_count == 3
    assert result.covered_pixels == 33 * 16
    assert result.missing_pixels == 0
    assert result.completed_local_plane_mosaic
    assert not result.orthophoto_verified


def test_missing_tile_and_duplicate_tiles_fail_closed():
    rows = tuple(mosaic(t) for t in PLAN.tiles)
    with pytest.raises(ValueError, match="inventory"):
        audit_rgb_roof_mosaic(PLAN, rows[:-1])
    with pytest.raises(ValueError, match="reordered"):
        audit_rgb_roof_mosaic(PLAN, (rows[0], rows[0], rows[2]))


def test_partial_coverage_counts_missing_pixels_correctly():
    rows = tuple(mosaic(t, valid=(i != 1)) for i, t in enumerate(PLAN.tiles))
    result = audit_rgb_roof_mosaic(PLAN, rows)
    assert result.missing_pixels == 16 * 16
    assert result.covered_fraction == pytest.approx((33 * 16 - 256) / (33 * 16))
    assert not result.completed_local_plane_mosaic
    assert not result.orthophoto_verified
