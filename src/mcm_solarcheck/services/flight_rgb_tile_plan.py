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
