"""Read-only deterministic composition of several RGB views of one metric roof tile.

Each input must already have individually verified intrinsics, camera pose,
undistorted RGB pixels and surveyed plane. Tile overlap merely detects multiple
image observations; it cannot independently verify geometric registration.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from mcm_solarcheck.domain.models import ImageFrame
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D
from mcm_solarcheck.services.rgb_surface_tiles import RGBSurfaceTile
from mcm_solarcheck.services.rgb_surface_tile_render import render_rgb_surface_tile


@dataclass(frozen=True)
class RGBMosaicSource:
    frame: ImageFrame
    undistorted_bgr: np.ndarray
    geometry: VerifiedCameraGeometry


@dataclass(frozen=True)
class RGBMosaicTile:
    tile: RGBSurfaceTile
    bgr: np.ndarray
    valid_mask: np.ndarray
    total_sources: int
    contributing_sources: int
    overlapping_observations: int
    mean_absolute_overlap_difference: float | None
    status: str = "unverified_multi_view_plane_preview"
    orthophoto_verified: bool = False


def compose_rgb_roof_tile(
    sources: tuple[RGBMosaicSource, ...],
    plane: SurveyedPlane3D,
    tile: RGBSurfaceTile,
    *,
    max_sources: int = 16,
) -> RGBMosaicTile:
    """First observation owns a pixel; later sources fill previously empty cells.

    Does not infer a planar transform from a panorama or average misregistered
    RGB source pixels. Records overlap discrepancy as a warning metric only.
    """
    if (
        type(sources) is not tuple or not sources
        or type(max_sources) is not int or max_sources < 1
        or len(sources) > max_sources
    ):
        raise ValueError("one or more bounded calibrated RGB sources required")
    if not isinstance(tile, RGBSurfaceTile):
        raise TypeError("one explicitly planned metric tile required")
    if any(not isinstance(s, RGBMosaicSource) or not isinstance(s.frame, ImageFrame)
           for s in sources):
        raise TypeError("imported RGB source records required")
    identifiers = [s.frame.frame_id for s in sources]
    if any(not name for name in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError("unique nonempty RGB source identifiers required")
    h, w = tile.grid.height, tile.grid.width
    if any(type(d) is not int or d < 1 or d > 2048 for d in (h, w)):
        raise ValueError("bounded metric tile dimensions required")
    composed = np.zeros((h, w, 3), dtype=np.uint8)
    coverage = np.zeros((h, w), dtype=bool)
    contributors = 0
    overlaps = 0
    difference_total = 0.
    for src in sources:
        result = render_rgb_surface_tile(src.frame, src.undistorted_bgr,
                                         src.geometry, plane, tile)
        if result.covered_pixels:
            contributors += 1
        mutual = coverage & result.valid_mask
        n = int(np.count_nonzero(mutual))
        if n:
            first = composed[mutual].astype(np.int16)
            other = result.bgr[mutual].astype(np.int16)
            difference_total += float(np.abs(first - other).sum()) / 3.
            overlaps += n
        new = result.valid_mask & ~coverage
        composed[new] = result.bgr[new]
        coverage |= result.valid_mask
    return RGBMosaicTile(
        tile, composed, coverage, len(sources), contributors, overlaps,
        difference_total / overlaps if overlaps else None,
    )
