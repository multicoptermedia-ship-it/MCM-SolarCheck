"""Read OpenMVS 2.4 output geometry; copy its rendered RGBA into GeoTIFF.

This is a format adapter, not an orthoprojector. OpenMVS renders the pixels.
The pinned Mesh::ProjectOrthoTopDown contract defines the padded mesh box,
pixel spacing and axes. Its rounded Center TXT is insufficient for this.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np


class OrthomapFormatError(ValueError):
    """Fixed format descriptions safe to show without private mesh values."""


def mesh_bounds(path, checkpoint=lambda: None):
    """Stream the actual exported PLY vertices, retaining float32 semantics."""
    kinds = {'char': 'i1', 'uchar': 'u1', 'short': 'i2', 'ushort': 'u2',
             'int': 'i4', 'uint': 'u4', 'float': 'f4', 'double': 'f8',
             'float32': 'f4', 'float64': 'f8', 'uint8': 'u1', 'int8': 'i1'}
    with Path(path).open('rb') as stream:
        if stream.readline().rstrip(b'\r\n') != b'ply':
            raise OrthomapFormatError('OpenMVS-PLY-Kopf fehlt.')
        fmt, count, element, properties, first = None, None, None, [], None
        for _ in range(2048):
            line = stream.readline(4097)
            if not line or len(line) > 4096:
                raise OrthomapFormatError('OpenMVS-PLY-Kopf ungueltig.')
            words = line.decode('ascii').split()
            if not words or words[0] in ('comment', 'obj_info'):
                continue
            if words[0] == 'end_header':
                break
            if words[0] == 'format':
                fmt = words[1]
            elif words[0] == 'element':
                element = words[1]
                first = first or element
                if element == 'vertex':
                    count = int(words[2])
            elif words[0] == 'property' and element == 'vertex':
                if len(words) != 3 or words[1] not in kinds:
                    raise OrthomapFormatError('OpenMVS-Vertexformat nicht unterstuetzt.')
                properties.append((words[2], kinds[words[1]]))
        else:
            raise OrthomapFormatError('OpenMVS-PLY-Kopf zu gross.')
        if (first != 'vertex' or count is None or not 3 <= count <= 20_000_000
                or fmt not in ('ascii', 'binary_little_endian', 'binary_big_endian')
                or not {'x', 'y', 'z'} <= {p[0] for p in properties}
                or len(set(p[0] for p in properties)) != len(properties)):
            raise OrthomapFormatError('OpenMVS-Vertexdaten ungueltig.')
        dtype = np.dtype(properties).newbyteorder('>' if fmt == 'binary_big_endian' else '<')
        lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
        for start in range(0, count, 65536):
            checkpoint()
            size = min(65536, count - start)
            if fmt == 'ascii':
                lines = [stream.readline(4097).split() for _ in range(size)]
                if any(len(line) != len(properties) for line in lines):
                    raise OrthomapFormatError('OpenMVS-Vertexdaten unvollstaendig.')
                block = np.array([tuple(line) for line in lines], dtype=dtype)
            else:
                block = np.fromfile(stream, dtype=dtype, count=size)
                if len(block) != size:
                    raise OrthomapFormatError('OpenMVS-Vertexdaten unvollstaendig.')
            xyz = np.column_stack([block[k] for k in ('x', 'y', 'z')])
            if not np.isfinite(xyz).all():
                raise OrthomapFormatError('OpenMVS-Vertexdaten nicht endlich.')
            lo, hi = np.minimum(lo, xyz.min(axis=0)), np.maximum(hi, xyz.max(axis=0))
    return lo.astype('float32'), hi.astype('float32')


def orthomap_reference(bounds, resolution, width, height, origin):
    """Recover raster metadata from the pinned top-down export, not TXT Center.

    Camera image x is world +x, image y is world -y. GDAL refers to pixel
    corners; OpenMVS centers its principal point at ((width-1)/2,(height-1)/2).
    The AABB and 1.01 border are float32 in OpenMVS; K is double precision.
    """
    from rasterio.transform import Affine

    lo, hi = (np.asarray(v, dtype='float32') for v in bounds)
    size = (hi - lo) * np.float32(1.01)
    center = (lo + hi) * np.float32(.5)
    if (not 2 <= resolution <= 16384 or not np.isfinite(size).all()
            or not np.isfinite(center).all() or min(size[:2]) <= 0
            or len(origin) != 3 or not all(math.isfinite(v) for v in origin)):
        raise OrthomapFormatError('OpenMVS-Rastergeometrie ungueltig.')
    sx, sy = (float(v) for v in size[:2])
    expected = ((resolution, math.ceil(sy * (resolution - 1) / sx)) if sx > sy
                else (math.ceil(sx * (resolution - 1) / sy), resolution))
    if (width, height) != expected:
        raise OrthomapFormatError('Orthomap-Groesse passt nicht zur OpenMVS-Meshgeometrie.')
    spacing = max(sx, sy) / (resolution - 1)
    return Affine(spacing, 0, origin[0] + float(center[0]) - width * spacing / 2,
                  0, -spacing, origin[1] + float(center[1]) + height * spacing / 2)


def copy_orthomap_geotiff(png, mesh, destination, *, crs, origin, resolution, checkpoint=lambda: None):
    import rasterio
    from rasterio.enums import ColorInterp
    from mcm_solarcheck.services.orthomosaic_geotiff_contract import inspect_existing_geotiff

    bounds = mesh_bounds(mesh, checkpoint)
    with rasterio.open(png) as src:
        if src.driver != 'PNG' or src.count != 4 or set(src.dtypes) != {'uint8'}:
            raise OrthomapFormatError('OpenMVS muss ein RGBA-Orthomap-PNG liefern.')
        transform = orthomap_reference(bounds, resolution, src.width, src.height, origin)
        alpha = src.read(4)
        if not np.isin(alpha, (0, 255)).all() or not alpha.any():
            raise OrthomapFormatError('OpenMVS-Orthomap besitzt keine verwendbare Datenmaske.')
        with rasterio.open(destination, 'w', driver='GTiff', width=src.width, height=src.height,
                           count=4, dtype='uint8', crs=crs.to_wkt(), transform=transform,
                           compress='deflate', nodata=None) as dst:
            for _, window in dst.block_windows(1):
                checkpoint()
                dst.write(src.read(window=window), window=window)
            dst.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)
            dst.update_tags(MCM_SOURCE='COLMAP_OpenMVS_RGB_PILOT',
                            MCM_GEOREFERENCE='camera_gnss_unverified',
                            MCM_PRODUCT_STATUS='unverified_display_raster')
    inspect_existing_geotiff(destination)
    return {'transform': list(transform)[:6], 'pixel_size_m': transform.a,
            'mesh_min_local': bounds[0].tolist(), 'mesh_max_local': bounds[1].tolist()}
