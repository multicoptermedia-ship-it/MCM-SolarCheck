"""Bounded RGB tile-source regression tests."""
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_tile_plan import RGBTile
from mcm_solarcheck.services.flight_rgb_tile_source import RGBArrayTileSource


def test_read_window_without_loading_full_array(tmp_path):
    source = np.arange(7 * 9 * 3, dtype=np.uint8).reshape(7, 9, 3)
    path = tmp_path / "rgb.npy"
    np.save(path, source)
    reader = RGBArrayTileSource(path, max_tile_pixels=6)
    assert (reader.height, reader.width) == (7, 9)
    tile = reader.read_tile(RGBTile(7, 5, 2, 2))
    np.testing.assert_array_equal(tile, source[5:7, 7:9])
    tile[:] = 0
    np.testing.assert_array_equal(np.load(path), source)


@pytest.mark.parametrize("tile", [
    RGBTile(-1, 0, 1, 1), RGBTile(0, 0, 0, 1),
    RGBTile(8, 0, 2, 1), RGBTile(0, 0, 3, 3),
])
def test_reject_invalid_or_oversized_windows(tmp_path, tile):
    path = tmp_path / "rgb.npy"
    np.save(path, np.zeros((7, 9, 3), dtype=np.uint8))
    with pytest.raises(ValueError):
        RGBArrayTileSource(path, max_tile_pixels=6).read_tile(tile)
