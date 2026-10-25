"""Bounded, cancellable, ephemeral multi-frame RGB roof-plane pilot.

This is not automatic SfM, GIS georeferencing, a finished full-flight
orthophoto, an image-loader or a database job. Calibrated/undistorted source
frames, verified plane and tile grid MUST be independently supplied.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D
from mcm_solarcheck.services.rgb_surface_tiles import RGBSurfaceTilePlan
from mcm_solarcheck.services.rgb_surface_tile_mosaic import (
    RGBMosaicSource, RGBMosaicTile, compose_rgb_roof_tile,
)
from mcm_solarcheck.services.rgb_surface_mosaic_audit import (
    RGBMosaicCoverageAudit, audit_rgb_roof_mosaic,
)


class RGBSurfacePilotCancelled(Exception):
    """Processing cancelled without writing RGB images or project state."""


@dataclass(frozen=True)
class RGBSurfacePilotRun:
    tiles: tuple[RGBMosaicTile, ...]
    audit: RGBMosaicCoverageAudit
    rgb_source_count: int
    processed_tile_count: int
    state: str
    orthophoto_verified: bool = False
    read_only: bool = True


def run_read_only_rgb_surface_pilot(
    plan: RGBSurfaceTilePlan,
    sources: tuple[RGBMosaicSource, ...],
    plane: SurveyedPlane3D,
    *,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[int, int, int], None] | None = None,
    max_tiles: int = 64,
    max_output_pixels: int = 12_000_000,
    max_sources: int = 16,
) -> RGBSurfacePilotRun:
    """Process one already calibrated roof-plane series entirely in RAM.

    A callback receives (finished_tiles, total_tiles, cumulative_covered_pixels).
    No path, GPS or customer data are included. Failure/cancellation returns no
    persisted result and has no rollback side effects.
    """
    if not isinstance(plan, RGBSurfaceTilePlan):
        raise TypeError("explicit native metric RGB tile plan required")
    if not isinstance(plane, SurveyedPlane3D):
        raise TypeError("explicit surveyed roof plane required")
    if type(sources) is not tuple or not sources or any(
        not isinstance(s, RGBMosaicSource) for s in sources
    ):
        raise TypeError("nonempty tuple of already prepared RGB sources required")
    if any(type(v) is not int or v <= 0 for v in (
        max_tiles, max_output_pixels, max_sources,
    )):
        raise ValueError("positive resource budgets required")
    if (
        not plan.tiles or len(plan.tiles) > max_tiles or len(sources) > max_sources
        or plan.width * plan.height > max_output_pixels
        or sum(t.grid.width * t.grid.height for t in plan.tiles) != plan.width * plan.height
    ):
        raise ValueError("RGB pilot exceeds tile, source, or pixel budget")
    cancelled = should_cancel or (lambda: False)
    if cancelled():
        raise RGBSurfacePilotCancelled()
    result_tiles = []
    coverage_so_far = 0
    for tile in plan.tiles:
        if cancelled():
            raise RGBSurfacePilotCancelled()
        tile_result = compose_rgb_roof_tile(
            sources, plane, tile, max_sources=max_sources,
        )
        result_tiles.append(tile_result)
        coverage_so_far += int(tile_result.valid_mask.sum())
        if on_progress is not None:
            on_progress(len(result_tiles), len(plan.tiles), coverage_so_far)
        if cancelled():
            raise RGBSurfacePilotCancelled()
    audit = audit_rgb_roof_mosaic(plan, tuple(result_tiles))
    if cancelled():
        raise RGBSurfacePilotCancelled()
    return RGBSurfacePilotRun(
        tuple(result_tiles), audit, len(sources), len(result_tiles),
        "local_plane_coverage_unverified" if audit.completed_local_plane_mosaic
        else "partial_or_missing_coverage_unverified",
    )
