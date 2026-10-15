"""Export native, surveyed planar RGB and thermal orthophotos as separate GeoTIFFs."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine

from mcm_solarcheck.services.orthomosaic_geotiff_contract import (
    GeoTIFFSpatialReference, require_geotiff_export_target,
    write_georeferenced_rgb_geotiff,
)
from mcm_solarcheck.services.orthophoto_planar_mosaic import build_planar_orthophoto
from mcm_solarcheck.services.orthophoto_planar_rectification import SurveyedFrame


def export_planar_orthophoto(
    frames: tuple[SurveyedFrame, ...],
    destination: str | Path,
    reference: GeoTIFFSpatialReference,
    *,
    thermal: bool = False,
    planar_surface_verified: bool = False,
) -> Path:
    """Generate from original frames, then export without overwriting.

    A thermal GeoTIFF contains source raster values, NOT claimed temperatures.
    """
    if planar_surface_verified is not True:
        raise ValueError("verified planar surface model is required")
    target = require_geotiff_export_target(destination, reference)
    if reference.nodata is not None:
        raise ValueError("this fully covered planar workflow requires nodata=None")
    image = build_planar_orthophoto(frames, reference, thermal=thermal)
    if not thermal:
        return write_georeferenced_rgb_geotiff(
            image, target, reference, georeferencing_verified=True,
        )
    if image.ndim != 2 or image.dtype.kind not in "uif":
        raise ValueError("thermal source must be numeric single-band")
    if image.dtype not in (np.dtype("uint8"), np.dtype("uint16"), np.dtype("float32")):
        raise ValueError("unsupported thermal GeoTIFF dtype")
    crs = CRS.from_user_input(reference.crs)
    fd, temporary_name = tempfile.mkstemp(
        prefix=".mcm-thermal-", suffix=".tif", dir=target.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with rasterio.open(
            temporary, "w", driver="GTiff",
            height=reference.height, width=reference.width,
            count=1, dtype=image.dtype, crs=crs,
            transform=Affine(*reference.transform),
        ) as dataset:
            dataset.write(image, 1)
            dataset.update_tags(
                MCM_THERMAL_CALIBRATION="unverified",
                MCM_ORTHOPHOTO_MODEL="surveyed_planar",
            )
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
