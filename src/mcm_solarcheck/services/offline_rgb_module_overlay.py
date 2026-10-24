"""Read-only diagnostic overlay of the existing three RGB module detectors.

Only one of the first three imported frames may be rendered, after checking
its stored import SHA-256 against the original bytes. The returned PNG stays
in memory and is a *diagnostic*, never evidence of confirmed PV modules.
No private paths, filenames or source pixels are persisted.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import cv2
import numpy as np

from mcm_solarcheck.services.offline_cadence_diagnostics import safe_cadence_reason
from mcm_solarcheck.services.offline_module_sample import (
    MAX_SAMPLE_FRAMES, ModuleSampleCancelled, _sample_entries, _verified_bgr,
)
from mcm_solarcheck.services.offline_processing_inventory import (
    capture_offline_processing_inventory,
)
from mcm_solarcheck.vision.cadence_module_detector import CadenceConfirmedModuleDetector
from mcm_solarcheck.vision.grid_module_backend import GridModuleDetector
from mcm_solarcheck.vision.module_fusion import fuse_module_detections
from mcm_solarcheck.vision.module_quality import filter_module_detections
from mcm_solarcheck.vision.opencv_module_detector import OpenCVModuleDetector

MAX_PREVIEW_SIDE = 960
MAX_MARKERS_PER_KIND = 300
MAX_PNG_BYTES = 8_000_000


@dataclass(frozen=True)
class RgbModuleOverlay:
    """One ephemeral local PNG plus count-only diagnostic metadata."""
    sample_index: int
    total: int
    png: bytes
    structural: int
    visual: int
    overlapping: int
    cadence: int
    cadence_reason: str
    read_only: bool = True


def _draw_proposals(canvas, proposals, scale, bgr_color, *, max_markers=MAX_MARKERS_PER_KIND):
    if len(proposals) > max_markers:
        raise ValueError("too many diagnostic polygons to draw safely")
    for detection in proposals:
        poly = detection.polygon_px
        if not 3 <= len(poly) <= 24:
            continue
        if not all(
            isfinite(float(x)) and isfinite(float(y))
            for x, y in poly
        ):
            continue
        points = np.asarray([
            (
                round(max(0, min(canvas.shape[1] - 1, float(x) * scale))),
                round(max(0, min(canvas.shape[0] - 1, float(y) * scale))),
            )
            for x, y in poly
        ], dtype=np.int32).reshape((-1, 1, 2))
        if len(np.unique(points.reshape((-1, 2)), axis=0)) < 3:
            continue
        cv2.polylines(canvas, [points], True, bgr_color, 2, cv2.LINE_AA)


def render_imported_rgb_module_overlay(
    database, project_id: str, *, sample_index: int = 0,
    should_cancel=None, grid_detector=None, image_detector=None,
    cadence_detector=None,
) -> RgbModuleOverlay:
    """Render one SHA-authenticated RGB preview, without a single file write.

    The 0-based index refers only to the first three imported RGB frames.
    This API deliberately cannot search arbitrary private paths or projects.
    """
    if type(sample_index) is not int or not 0 <= sample_index < MAX_SAMPLE_FRAMES:
        raise ValueError("sample index outside read-only three-frame limit")
    cancelled = should_cancel or (lambda: False)
    if cancelled():
        raise ModuleSampleCancelled()

    before = capture_offline_processing_inventory(database, project_id)
    entries = _sample_entries(database, project_id)
    total = min(before.rgb_frames, MAX_SAMPLE_FRAMES)
    if len(entries) != total or sample_index >= total:
        raise ValueError("RGB sample inventory or index invalid")

    source, width, height, digest = entries[sample_index]
    bgr, status = _verified_bgr(source, width, height, digest, cancelled)
    if status != "ok" or bgr is None:
        raise ValueError("image could not be authenticated for preview")
    if cancelled():
        raise ModuleSampleCancelled()

    grid = grid_detector or GridModuleDetector()
    image = image_detector or OpenCVModuleDetector()
    cadence_detector = cadence_detector or CadenceConfirmedModuleDetector()
    geometry, _ = grid.detect_with_diagnostics_array(bgr)
    if cancelled():
        raise ModuleSampleCancelled()
    visual = image.detect_array(bgr)
    if cancelled():
        raise ModuleSampleCancelled()
    found = fuse_module_detections(
        tuple(geometry), tuple(visual), minimum_iou=.20,
    )
    overlap = filter_module_detections(
        found, bgr.shape[1], bgr.shape[0],
    )
    cadence, reason = cadence_detector.detect_array_with_status(bgr)
    if cancelled():
        raise ModuleSampleCancelled()

    # Render the original pixel-aligned proposals on a bounded, separate
    # preview array. Never draw onto original files or original RGB arrays.
    native_height, native_width = bgr.shape[:2]
    scale = min(1.0, MAX_PREVIEW_SIDE / max(native_height, native_width))
    canvas = (
        cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        if scale < 1 else bgr.copy()
    )
    del bgr
    # OpenCV BGR: yellow = structural, magenta = image-based,
    # turquoise = mutually overlapping, green = cadence suggestions.
    _draw_proposals(canvas, geometry, scale, (0, 220, 255))
    _draw_proposals(canvas, visual, scale, (215, 30, 255))
    _draw_proposals(canvas, overlap, scale, (255, 255, 0))
    _draw_proposals(canvas, cadence, scale, (70, 225, 70))
    if cancelled():
        raise ModuleSampleCancelled()
    success, encoded = cv2.imencode(
        ".png", canvas, [cv2.IMWRITE_PNG_COMPRESSION, 4],
    )
    if not success:
        raise ValueError("preview PNG encoder failed")
    png = encoded.tobytes()
    del canvas, encoded
    if len(png) > MAX_PNG_BYTES:
        raise ValueError("preview exceeds local memory bound")

    after = capture_offline_processing_inventory(database, project_id)
    if before.fingerprint != after.fingerprint:
        raise ValueError("project changed while preview was generated")
    if cancelled():
        raise ModuleSampleCancelled()
    return RgbModuleOverlay(
        sample_index=sample_index, total=total, png=png,
        structural=len(geometry), visual=len(visual), overlapping=len(overlap),
        cadence=len(cadence), cadence_reason=(
            "spatially_supported" if cadence else safe_cadence_reason(reason)
        ),
    )
