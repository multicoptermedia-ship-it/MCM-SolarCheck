"""Synthetic exported-file tests, not a reconstruction/quality certification."""
import struct

import numpy as np
from PIL import Image
from pyproj import CRS
import pytest
import rasterio

from mcm_solarcheck.services.openmvs_orthomap import (
    copy_orthomap_geotiff, mesh_bounds, orthomap_reference,
)


def write_mesh(path, fmt='binary_little_endian', vertices=None):
    vertices = vertices if vertices is not None else [(0, 0, 0), (10, 0, 1), (0, 5, 1), (10, 5, 2)]
    header = ('ply\nformat ' + fmt + ' 1.0\ncomment TextureFile textured0.png\n'
              f'element vertex {len(vertices)}\nproperty float x\nproperty float y\nproperty float z\n'
              'property float nx\nproperty float ny\nproperty float nz\n'
              'element face 1\nproperty list uchar int vertex_indices\nend_header\n')
    with path.open('wb') as stream:
        stream.write(header.encode())
        for row in vertices:
            if fmt == 'ascii':
                stream.write((' '.join(map(str, (*row, 0, 0, 1))) + '\n').encode())
            else:
                stream.write(struct.pack(('>' if fmt == 'binary_big_endian' else '<') + '6f', *row, 0, 0, 1))
        # Deliberately huge face indices must not contaminate vertex bounds.
        stream.write(b'3 10000000 10000001 10000002\n')


@pytest.mark.parametrize('fmt', ['ascii', 'binary_little_endian', 'binary_big_endian'])
def test_actual_vertex_bounds_ignore_faces_and_normals(tmp_path, fmt):
    path = tmp_path / 'textured.ply'
    write_mesh(path, fmt)
    lo, hi = mesh_bounds(path)
    np.testing.assert_array_equal(lo, [0, 0, 0])
    np.testing.assert_array_equal(hi, [10, 5, 2])
    assert lo.dtype == hi.dtype == np.dtype('float32')


@pytest.mark.parametrize('resolution,width,height', [(128, 128, 64), (129, 129, 64)])
def test_landscape_pixel_centers_and_north_up(resolution, width, height):
    # Independently specified mesh midpoint, corner convention and 1.01 border.
    bounds = ((-2, -4, 0), (8, 1, 2))
    pitch = float(np.float32(10.1)) / (resolution - 1)
    tr = orthomap_reference(bounds, resolution, width, height, [500000, 5500000, 100])
    assert tr.a == pytest.approx(pitch) and tr.e == pytest.approx(-pitch)
    np.testing.assert_allclose(tr * (width / 2, height / 2), [500003, 5499998.5])
    np.testing.assert_allclose(tr * (.5, .5),
                               [500003 - (width-1)/2*pitch, 5499998.5 + (height-1)/2*pitch])


def test_portrait_even_dimensions_use_actual_ceiling_not_square_pixels_extent_guess():
    tr = orthomap_reference(((0, 0, -2), (4, 10, 1)), 128, 51, 128, [1000, 2000, 140])
    np.testing.assert_allclose(tr * (51/2, 64), [1002, 2005])
    with pytest.raises(ValueError, match='Groesse'):
        orthomap_reference(((0, 0, -2), (4, 10, 1)), 128, 52, 128, [1000, 2000, 140])


def test_copy_preserves_rgba_and_valid_black_then_reopens(tmp_path):
    mesh, png, output = (tmp_path / n for n in ('textured.ply', 'orthomap.png', 'rgb.tif'))
    write_mesh(mesh)
    pixels = np.full((64, 128, 4), (30, 60, 90, 255), dtype='uint8')
    pixels[:, 0, 3] = 0
    pixels[3, 3, :3] = 0
    Image.fromarray(pixels).save(png)
    meta = copy_orthomap_geotiff(png, mesh, output, crs=CRS.from_epsg(32632),
                                origin=[500000, 5500000, 140], resolution=128)
    with rasterio.open(output) as src:
        np.testing.assert_array_equal(src.read().transpose(1, 2, 0), pixels)
        assert not src.dataset_mask()[:, 0].any()
        assert src.dataset_mask()[3, 3] == 255  # black is data, not a guessed NoData
        assert src.crs.to_epsg() == 32632 and src.nodata is None
        assert src.transform.a == meta['pixel_size_m']
        assert src.tags()['MCM_PRODUCT_STATUS'] == 'unverified_display_raster'
        np.testing.assert_allclose(src.transform * (64, 32), [500005, 5500002.5])


@pytest.mark.parametrize('failure', ['truncated', 'nonfinite', 'wrong_size', 'missing_alpha', 'empty_alpha'])
def test_invalid_outputs_never_get_a_guessed_reference(tmp_path, failure):
    mesh, png, output = (tmp_path / n for n in ('textured.ply', 'orthomap.png', 'rgb.tif'))
    write_mesh(mesh)
    pixels = np.full((64, 128, 4), 255, dtype='uint8')
    if failure == 'truncated':
        mesh.write_bytes(mesh.read_bytes()[:mesh.read_bytes().index(b'end_header') + 11])
    elif failure == 'nonfinite':
        write_mesh(mesh, vertices=[(0, 0, 0), (float('nan'), 5, 2), (10, 0, 2)])
    elif failure == 'wrong_size':
        pixels = pixels[:, :-1]
    elif failure == 'missing_alpha':
        pixels = pixels[:, :, :3]
    else:
        pixels[:, :, 3] = 0
    Image.fromarray(pixels).save(png)
    with pytest.raises(ValueError):
        copy_orthomap_geotiff(png, mesh, output, crs=CRS.from_epsg(32632),
                             origin=[500000, 5500000, 140], resolution=128)
    assert not output.exists()
