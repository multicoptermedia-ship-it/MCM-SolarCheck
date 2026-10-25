"""Count-only audit for a complete expected RGB plane-tile set.

Mosaic overlap is not proof that all camera poses are correct. No client pixels,
GPS, customer names or paths are emitted by this diagnostic.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from mcm_solarcheck.services.rgb_surface_tiles import RGBSurfaceTilePlan
from mcm_solarcheck.services.rgb_surface_tile_mosaic import RGBMosaicTile


@dataclass(frozen=True)
class RGBMosaicCoverageAudit:
    tile_count: int
    covered_pixels: int
    missing_pixels: int
    tile_fraction_complete: float
    covered_fraction: float
    overlapping_observations: int
    completed_local_plane_mosaic: bool
    orthophoto_verified: bool = False


def audit_rgb_roof_mosaic(
    plan: RGBSurfaceTilePlan,
    mosaics: tuple[RGBMosaicTile, ...],
) -> RGBMosaicCoverageAudit:
    """All planned tiles must be returned in canonical row-major order."""
    if not isinstance(plan, RGBSurfaceTilePlan) or not isinstance(mosaics, tuple):
        raise TypeError("explicit plan and mosaic tile tuple required")
    if len(mosaics) != len(plan.tiles):
        raise ValueError("mosaic outputs do not cover planned tile inventory")
    pixels = complete = overlap = 0
    for expected, mosaic in zip(plan.tiles, mosaics):
        if not isinstance(mosaic, RGBMosaicTile) or mosaic.tile != expected:
            raise ValueError("missing, duplicated or reordered mosaic tile")
        h, w = expected.grid.height, expected.grid.width
        if (
            not isinstance(mosaic.valid_mask, np.ndarray)
            or mosaic.valid_mask.dtype != np.bool_
            or mosaic.valid_mask.shape != (h, w)
            or not isinstance(mosaic.bgr, np.ndarray)
            or mosaic.bgr.shape != (h, w, 3)
            or mosaic.bgr.dtype != np.uint8
        ):
            raise ValueError("tile RGB pixels and validity mask mismatch")
        n = int(np.count_nonzero(mosaic.valid_mask))
        pixels += n
        complete += int(n == h * w)
        if type(mosaic.overlapping_observations) is not int or mosaic.overlapping_observations < 0:
            raise ValueError("invalid source overlap counter")
        overlap += mosaic.overlapping_observations
    total = plan.width * plan.height
    if total < 1 or total != sum(t.grid.width * t.grid.height for t in plan.tiles):
        raise ValueError("planned surface area mismatch")
    return RGBMosaicCoverageAudit(
        len(plan.tiles), pixels, total - pixels,
        complete / len(plan.tiles), pixels / total, overlap, bool(pixels == total),
    )
