"""Bounded window access to explicitly supported on-disk RGB arrays.

Only uncompressed, C-contiguous uint8 RGB .npy arrays are supported.
This is NOT a JPEG/PNG region decoder or a georeferenced image reader.
"""
from pathlib import Path

import numpy as np

from mcm_solarcheck.services.flight_rgb_tile_plan import RGBTile, iter_rgb_tiles


class RGBArrayTileSource:
    """Read tile windows from a memory-mapped, immutable .npy RGB array."""

    def __init__(self, path, *, max_tile_pixels=1_048_576):
        self.path = Path(path)
        if self.path.is_symlink() or not self.path.is_file() or self.path.suffix.lower() != ".npy":
            raise ValueError("regular .npy RGB array required")
        if type(max_tile_pixels) is not int or max_tile_pixels < 1:
            raise ValueError("invalid tile pixel budget")
        self.max_tile_pixels = max_tile_pixels
        self._array = np.load(self.path, mmap_mode="r", allow_pickle=False)
        if (self._array.ndim != 3 or self._array.shape[2] != 3
                or self._array.dtype != np.dtype("uint8")
                or not self._array.flags.c_contiguous):
            raise ValueError("C-contiguous uint8 HxWx3 RGB array required")
        self.height, self.width = self._array.shape[:2]

    def read_tile(self, tile):
        if not isinstance(tile, RGBTile):
            raise TypeError("RGBTile required")
        if (min(tile.x, tile.y) < 0 or min(tile.width, tile.height) <= 0
                or tile.x + tile.width > self.width
                or tile.y + tile.height > self.height
                or tile.width * tile.height > self.max_tile_pixels):
            raise ValueError("RGB tile outside bounds or pixel budget")
        return np.array(self._array[tile.y:tile.y + tile.height,
                                    tile.x:tile.x + tile.width], copy=True)

    def iter_tiles(self, *, tile_side=512):
        """Yield one bounded copied RGB tile at a time; no tile batch is retained."""
        for tile in iter_rgb_tiles(self.width, self.height, tile_side=tile_side,
                                   max_tile_pixels=self.max_tile_pixels):
            yield tile, self.read_tile(tile)
