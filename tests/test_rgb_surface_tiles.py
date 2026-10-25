"""Synthetic full-resolution pixel-coordinate tiling, no photos."""
import pytest

from mcm_solarcheck.services.rgb_surface_tiles import plan_rgb_surface_tiles
from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid


def test_plan_preserves_metric_grid_without_downsampling():
    grid = ModuleSurfaceGrid(-5., 10., .02, 1030, 1031)
    plan = plan_rgb_surface_tiles(grid, tile_side_px=512)
    assert (plan.width, plan.height, len(plan.tiles)) == (1030, 1031, 9)
    assert (plan.tiles[0].row, plan.tiles[0].column) == (0, 0)
    assert (plan.tiles[-1].row, plan.tiles[-1].column) == (2, 2)
    last = plan.tiles[-1].grid
    assert (last.width, last.height) == (6, 7)
    assert last.u_min_m == pytest.approx(-5 + 1024 * .02)
    assert last.v_min_m == pytest.approx(10 + 1024 * .02)
    assert sum(t.grid.width * t.grid.height for t in plan.tiles) == grid.width * grid.height
    assert not plan.georeferencing_verified
    assert not plan.rgb_orthophoto_verified


def test_tile_boundary_does_not_shift_pixel_centres():
    grid = ModuleSurfaceGrid(0, 0, .1, 33, 32)
    plan = plan_rgb_surface_tiles(grid, tile_side_px=16)
    assert len(plan.tiles) == 6
    first = plan.tiles[0].grid
    second = plan.tiles[1].grid
    x_last_first = first.u_min_m + (first.width - .5) * first.metres_per_pixel
    x_first_second = second.u_min_m + .5 * second.metres_per_pixel
    assert x_first_second - x_last_first == pytest.approx(.1)


@pytest.mark.parametrize("grid", [
    ModuleSurfaceGrid(0, 0, 0, 10, 10),
    ModuleSurfaceGrid(0, 0, .1, -1, 1),
    ModuleSurfaceGrid(float("nan"), 0, .1, 10, 10),
])
def test_invalid_metric_grid_fails_closed(grid):
    with pytest.raises(ValueError):
        plan_rgb_surface_tiles(grid)


def test_resource_budgets_fail_closed():
    with pytest.raises(ValueError, match="pixel budget"):
        plan_rgb_surface_tiles(ModuleSurfaceGrid(0, 0, .1, 2000, 2000),
                               max_total_pixels=100)
    with pytest.raises(ValueError, match="tile count"):
        plan_rgb_surface_tiles(ModuleSurfaceGrid(0, 0, .1, 300, 300),
                               tile_side_px=16, max_tiles=10)
    with pytest.raises(ValueError, match="tile size"):
        plan_rgb_surface_tiles(ModuleSurfaceGrid(0, 0, .1, 20, 20), tile_side_px=8)
