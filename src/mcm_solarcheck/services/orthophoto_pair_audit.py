"""Independent validation of RGB/thermal orthophoto geospatial overlap.

This does not certify ground accuracy or radiometric calibration.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rasterio.warp import transform_bounds

from mcm_solarcheck.services.orthophoto_layer_alignment import (
    aligned_preview_arrays, inspect_orthophoto_layer_pair,
)


@dataclass(frozen=True)
class OrthophotoPairAudit:
    rgb_path: Path
    thermal_path: Path
    rgb_crs: str
    thermal_crs: str
    common_pixel_fraction: float
    comparison_ready: bool
    georeferencing_verified: bool = False
    thermal_calibration_verified: bool = False


def audit_orthophoto_pair(rgb_path: str | Path, thermal_path: str | Path) -> OrthophotoPairAudit:
    """Require a finite overlapping preview, without asserting true ground accuracy."""
    pair = inspect_orthophoto_layer_pair(rgb_path, thermal_path)
    rgb, thermal = aligned_preview_arrays(pair)
    fraction = float(np.count_nonzero(np.isfinite(thermal))) / thermal.size
    return OrthophotoPairAudit(
        pair.rgb_path, pair.thermal_path,
        pair.rgb_reference.crs, pair.thermal_reference.crs,
        fraction, bool(fraction > 0 and rgb.shape[:2] == thermal.shape),
    )
