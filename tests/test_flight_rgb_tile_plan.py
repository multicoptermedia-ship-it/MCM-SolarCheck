"""Tests for nonmetric RGB tile planning, without full-frame allocation."""
import pytest

from mcm_solarcheck.services.flight_rgb_tile_plan import RGBTile, iter_rgb_tiles, plan_rgb_tile_batch


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


def test_bounded_materialized_tile_plan():
    assert len(plan_rgb_tile_batch(1024, 1024, tile_side=512, max_tiles=4)) == 4
    with pytest.raises(ValueError, match="tile count"):
        plan_rgb_tile_batch(1025, 1024, tile_side=512, max_tiles=4)


def test_large_tile_iterator_is_lazy():
    iterator = iter_rgb_tiles(10**9, 10**9, tile_side=512)
    assert next(iterator) == RGBTile(0, 0, 512, 512)
    assert next(iterator) == RGBTile(512, 0, 512, 512)
