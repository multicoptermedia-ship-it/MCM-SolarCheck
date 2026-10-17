"""Create a bounded, local report illustration from an existing RGB GeoTIFF.

This is a preview for reviewed reports, not orthophoto generation or flight-path proof.
"""
from __future__ import annotations

from pathlib import Path
import os
import tempfile

import numpy as np
from PIL import Image
import rasterio

from mcm_solarcheck.services.orthomosaic_geotiff_contract import inspect_existing_geotiff
from mcm_solarcheck.services.pv_pilot_flight_overview import PilotFlightOverview


def create_rgb_orthophoto_report_preview(
    geotiff: str | Path,
    destination: str | Path,
    *,
    max_side: int = 1800,
) -> PilotFlightOverview:
    """Downsample a CRS-bearing three-band RGB GeoTIFF to a report-only PNG."""
    source = Path(geotiff)
    target = Path(destination)
    if source.resolve() == target.resolve():
        raise ValueError("report preview must not replace the source orthophoto")
    if target.suffix.lower() != ".png" or not target.parent.is_dir():
        raise ValueError("report preview requires an existing directory and PNG destination")
    if target.exists():
        raise FileExistsError("report preview already exists")
    if type(max_side) is not int or not 1 <= max_side <= 4096:
        raise ValueError("bounded positive preview dimension required")
    reference = inspect_existing_geotiff(source)
    width, height = reference.width, reference.height
    scale = min(1., max_side / max(width, height))
    out_w, out_h = max(1, int(round(width * scale))), max(1, int(round(height * scale)))
    with rasterio.open(source) as dataset:
        if dataset.count != 3 or dataset.dtypes != ("uint8",) * 3:
            raise ValueError("report overview requires an RGB uint8 three-band GeoTIFF")
        from rasterio.enums import ColorInterp, Resampling
        if dataset.colorinterp[:3] != (ColorInterp.red, ColorInterp.green, ColorInterp.blue):
            raise ValueError("RGB band semantics must be explicit")
        bands = dataset.read((1, 2, 3), out_shape=(3, out_h, out_w), resampling=Resampling.nearest)
    rgb = np.moveaxis(bands, 0, 2)
    fd, name = tempfile.mkstemp(prefix=".mcm-report-ortho-", suffix=".png", dir=target.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        Image.fromarray(rgb, "RGB").save(temporary, format="PNG")
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return PilotFlightOverview(
        image_path=target, path_kind="not_available",
        source_note="RGB-GeoTIFF-Vorschau (verkleinert); kein Flugpfadnachweis; keine thermische Kalibrierung",
    )
