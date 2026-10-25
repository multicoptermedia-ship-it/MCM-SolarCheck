"""Bounded, deterministic tiles of an explicitly supplied metric RGB roof grid.

Only a memory-safe local *plan* is constructed; not a metric orthophoto.
Each tile is on the existing true tilted-plane (u,v) coordinate system.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite

from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid


@dataclass(frozen=True)
class RGBSurfaceTile:
    row: int
    column: int
    grid: ModuleSurfaceGrid


@dataclass(frozen=True)
class RGBSurfaceTilePlan:
    width: int
    height: int
    tile_side_px: int
    tiles: tuple[RGBSurfaceTile, ...]
    georeferencing_verified: bool = False
    rgb_orthophoto_verified: bool = False


def plan_rgb_surface_tiles(
    grid: ModuleSurfaceGrid, *,
    tile_side_px: int = 512,
    max_total_pixels: int = 250_000_000,
    max_tiles: int = 4096,
) -> RGBSurfaceTilePlan:
    """Partition a metric plane grid without allocating full-flight image arrays."""
    if not isinstance(grid, ModuleSurfaceGrid):
        raise TypeError("explicit planar metric grid required")
    if (
        type(grid.width) is not int or type(grid.height) is not int
        or grid.width < 1 or grid.height < 1
        or any(type(v) not in (int, float) or not isfinite(v) for v in
                (grid.u_min_m, grid.v_min_m, grid.metres_per_pixel))
        or grid.metres_per_pixel <= 0
    ):
        raise ValueError("finite positive grid dimensions and resolution required")
    if (
        any(type(v) is not int or v < 1 for v in
            (tile_side_px, max_total_pixels, max_tiles))
        or not 16 <= tile_side_px <= 2048
    ):
        raise ValueError("bounded integer tile size and resource budgets required")
    if grid.width * grid.height > max_total_pixels:
        raise ValueError("planned image area exceeds pixel budget")
    columns = ceil(grid.width / tile_side_px)
    rows = ceil(grid.height / tile_side_px)
    if rows * columns > max_tiles:
        raise ValueError("planned grid exceeds tile count budget")
    tiles = []
    for row in range(rows):
        y = row * tile_side_px
        height = min(tile_side_px, grid.height - y)
        for column in range(columns):
            x = column * tile_side_px
            width = min(tile_side_px, grid.width - x)
            subgrid = ModuleSurfaceGrid(
                grid.u_min_m + x * grid.metres_per_pixel,
                grid.v_min_m + y * grid.metres_per_pixel,
                grid.metres_per_pixel, width, height,
            )
            tiles.append(RGBSurfaceTile(row, column, subgrid))
    return RGBSurfaceTilePlan(grid.width, grid.height, tile_side_px, tuple(tiles))
