"""Count-only conservative audit of a rendered RGB roof-surface tile.

Pixels stay in memory. Coverage alone never certifies survey accuracy,
orthorectification, native detail, complete flight, roof extent or a GIS CRS.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from mcm_solarcheck.services.rgb_surface_tile_render import RGBRenderedSurfaceTile


@dataclass(frozen=True)
class RGBSurfaceTileAudit:
    row: int
    column: int
    width: int
    height: int
    covered_pixels: int
    missing_pixels: int
    covered_fraction: float
    state: str
    independent_survey_verified: bool = False
    photogrammetric_orthophoto_verified: bool = False


def audit_rgb_surface_tile(rendered: RGBRenderedSurfaceTile) -> RGBSurfaceTileAudit:
    """Return only bounded diagnostic counts, never original source pixels."""
    if not isinstance(rendered, RGBRenderedSurfaceTile):
        raise TypeError("rendered RGB metric tile required")
    h, w = rendered.tile.grid.height, rendered.tile.grid.width
    if (
        not isinstance(rendered.valid_mask, np.ndarray)
        or rendered.valid_mask.dtype != np.bool_
        or rendered.valid_mask.shape != (h, w)
        or not isinstance(rendered.bgr, np.ndarray)
        or rendered.bgr.dtype != np.uint8
        or rendered.bgr.shape != (h, w, 3)
    ):
        raise ValueError("tile color data and coverage mask must match declared grid")
    valid = int(np.count_nonzero(rendered.valid_mask))
    if valid != rendered.covered_pixels:
        raise ValueError("inconsistent rendered pixel coverage count")
    total = w * h
    state = "empty" if valid == 0 else "covered_unverified" if valid == total else "partial"
    return RGBSurfaceTileAudit(
        rendered.tile.row, rendered.tile.column, w, h,
        valid, total - valid, valid / total, state,
    )
