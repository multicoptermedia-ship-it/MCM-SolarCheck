"""Tests for nonmetric RGB tile planning, without full-frame allocation."""
import pytest

from mcm_solarcheck.services.flight_rgb_tile_plan import RGBTile, iter_rgb_tiles


def test_tiles_cover_nondivisible_dimensions():
    assert list(iter_rgb_tiles(5, 3, tile_side=2, max_tile_pixels=4)) == [
        RGBTile(0, 0, 2, 2), RGBTile(2, 0, 2, 2), RGBTile(4, 0, 1, 2),
        RGBTile(0, 2, 2, 1), RGBTile(2, 2, 2, 1), RGBTile(4, 2, 1, 1),
    ]


@pytest.mark.parametrize("kwargs", [
    {"width": 0, "height": 10}, {"width": 10, "height": -1},
    {"width": True, "height": 10},
    {"width": 10, "height": 10, "tile_side": 0},
    {"width": 10, "height": 10, "tile_side": 5, "max_tile_pixels": 24},
])
def test_invalid_tile_budgets_fail(kwargs):
    with pytest.raises(ValueError):
        list(iter_rgb_tiles(**kwargs))
