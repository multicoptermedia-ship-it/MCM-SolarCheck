"""Deterministic bounded tile planning for future nonmetric RGB processing.

Planning only: no image decoding, blending, georeferencing or output writing.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RGBTile:
    x: int
    y: int
    width: int
    height: int


def iter_rgb_tiles(width, height, *, tile_side=512, max_tile_pixels=1_048_576):
    """Yield rectangular tiles without allocating a full-image array."""
    for value in (width, height, tile_side, max_tile_pixels):
        if type(value) is not int or value <= 0:
            raise ValueError("positive integer RGB tile dimensions required")
    if tile_side * tile_side > max_tile_pixels:
        raise ValueError("RGB tile exceeds pixel budget")
    for y in range(0, height, tile_side):
        for x in range(0, width, tile_side):
            yield RGBTile(x, y, min(tile_side, width - x),
                          min(tile_side, height - y))


def plan_rgb_tile_batch(width, height, *, tile_side=512,
                        max_tile_pixels=1_048_576, max_tiles=4096):
    """Materialize only a capped plan; reject oversized plans explicitly."""
    if type(max_tiles) is not int or max_tiles < 1:
        raise ValueError("positive integer RGB tile count limit required")
    # Validate dimensions even for an empty or otherwise rejected plan.
    tiles = []
    for tile in iter_rgb_tiles(width, height, tile_side=tile_side,
                               max_tile_pixels=max_tile_pixels):
        if len(tiles) >= max_tiles:
            raise ValueError("RGB tile plan exceeds tile count limit")
        tiles.append(tile)
    return tuple(tiles)
