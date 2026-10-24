"""Cautious read-only 1..3 frame PV module detector feasibility sample.

Only verified imported RGB bytes are decoded; no modules, findings, reviews or
processing-run statuses are persisted. Candidate counts are NOT PV modules.
A module may be reported only after separate spatial/human validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from mcm_solarcheck.services.offline_processing_inventory import (
    capture_offline_processing_inventory,
)
from mcm_solarcheck.vision.grid_module_backend import GridModuleDetector
from mcm_solarcheck.vision.cadence_module_detector import CadenceConfirmedModuleDetector
from mcm_solarcheck.vision.opencv_module_detector import OpenCVModuleDetector
from mcm_solarcheck.vision.module_fusion import fuse_module_detections
from mcm_solarcheck.vision.module_quality import filter_module_detections

MAX_RGB_BYTES = 120_000_000
MAX_RGB_PIXELS = 64_000_000
MAX_SAMPLE_FRAMES = 3


class ModuleSampleCancelled(Exception):
    """Explicit stop during a read-only diagnostics sample."""


@dataclass(frozen=True)
class ModuleSampleResult:
    available_rgb: int
    sample_size: int
    checked: int
    analyzed: int
    issues: int
    unverified: int
    structural_proposals: int
    visual_proposals: int
    overlapping_proposals: int
    frames_with_overlap: int
    changed_inputs: bool
    read_only: bool = True
    cadence_proposals: int = 0
    cadence_frames_with_proposals: int = 0
    cadence_rejected_no_support: int = 0
    cadence_rejected_grid: int = 0
    cadence_rejected_phase: int = 0
    cadence_rejected_other: int = 0

    @property
    def technical_sample_only(self) -> bool:
        return True


def _sample_entries(database, project_id):
    with database.connect() as sql:
        return tuple(sql.execute(
            "SELECT f.source_file, f.width, f.height, t.content_sha256 "
            "FROM image_frames AS f LEFT JOIN training_samples AS t "
            "ON t.project_id=f.project_id AND t.source_frame_id=f.frame_id "
            "AND t.modality='rgb' WHERE f.project_id=? "
            "ORDER BY f.frame_id LIMIT ?",
            (project_id, MAX_SAMPLE_FRAMES),
        ))


def _verified_bgr(source, width, height, checksum, should_cancel):
    """Return only unchanged, SHA-matching first-picture RGB pixels in memory."""
    path = Path(source)
    if path.is_symlink() or not path.is_file():
        return None, "issue"
    if not isinstance(checksum, str) or len(checksum) != 64:
        return None, "unverified"
    if any(char not in "0123456789abcdefABCDEF" for char in checksum):
        return None, "unverified"
    try:
        initial = path.stat()
        if initial.st_size <= 0 or initial.st_size > MAX_RGB_BYTES:
            return None, "issue"
        h = sha256()
        fragments = []
        n = 0
        with path.open("rb") as stream:
            while True:
                if should_cancel():
                    raise ModuleSampleCancelled()
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                n += len(chunk)
                if n > MAX_RGB_BYTES:
                    return None, "issue"
                h.update(chunk)
                fragments.append(chunk)
        if n != initial.st_size or h.hexdigest() != checksum.lower():
            return None, "issue"
        data = b"".join(fragments)
        if should_cancel():
            raise ModuleSampleCancelled()
        with Image.open(BytesIO(data)) as image:
            if image.format not in ("JPEG", "MPO", "PNG", "TIFF"):
                return None, "issue"
            w, hh = image.size
            if w <= 0 or hh <= 0 or w * hh > MAX_RGB_PIXELS:
                return None, "issue"
            if (width is not None and w != width) or (
                height is not None and hh != height
            ):
                return None, "issue"
            # Pillow handles DJI MPO first image. Do not interpret other MPO
            # subframes as RGB sources or silently rotate coordinates.
            rgb = np.asarray(image.convert("RGB"))
        if should_cancel():
            raise ModuleSampleCancelled()
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        final = path.stat()
        if (
            final.st_size != initial.st_size
            or final.st_mtime_ns != initial.st_mtime_ns
            or final.st_ino != initial.st_ino
        ):
            return None, "issue"
        return bgr, "ok"
    except ModuleSampleCancelled:
        raise
    except (OSError, ValueError, TypeError, SyntaxError, cv2.error):
        return None, "issue"


def sample_imported_rgb_module_evidence(
    database, project_id, *, should_cancel=None, on_progress=None,
    grid_detector=None, image_detector=None, cadence_detector=None,
) -> ModuleSampleResult:
    """Read-only first-3 image feasibility test; output counts only.

    Grid proposals and visual proposals are independent, and only spatial
    overlap can yield overlapping proposals. In addition, the previously
    implemented cadence-aware detector is now evaluated on the SAME verified
    in-memory pixels. A cadence detection is still only a suggestion; a
    rejected cadence is technical evidence, not proof of no installed module.
    None of these counts are expert-confirmed PV modules.
    """
    cancelled = should_cancel or (lambda: False)
    if cancelled():
        raise ModuleSampleCancelled()
    initial = capture_offline_processing_inventory(database, project_id)
    entries = _sample_entries(database, project_id)
    sample_size = min(initial.rgb_frames, MAX_SAMPLE_FRAMES)
    if len(entries) != sample_size:
        raise ValueError("RGB inventory changed during sample selection")
    grid = grid_detector or GridModuleDetector()
    image = image_detector or OpenCVModuleDetector()
    cadence = cadence_detector or CadenceConfirmedModuleDetector()
    checked = analyzed = errors = missing = grids = visuals = overlaps = supported_frames = 0
    cadence_proposals = cadence_frames = no_support = no_grid = no_phase = other = 0
    for source, width, height, checksum in entries:
        if cancelled():
            raise ModuleSampleCancelled()
        bgr, condition = _verified_bgr(source, width, height, checksum, cancelled)
        checked += 1
        if condition == "unverified":
            missing += 1
        elif condition != "ok":
            errors += 1
        else:
            try:
                geometry, _ = grid.detect_with_diagnostics_array(bgr)
                support = image.detect_array(bgr)
                # Only geometrically valid, non-duplicate cell intersections
                # are counted; still not proof these cells are PV modules.
                found = fuse_module_detections(
                    tuple(geometry), tuple(support), minimum_iou=.20,
                )
                accepted = filter_module_detections(
                    found, bgr.shape[1], bgr.shape[0],
                )
                grids += len(geometry)
                visuals += len(support)
                overlaps += len(accepted)
                supported_frames += bool(accepted)
                if cancelled():
                    raise ModuleSampleCancelled()
                cadence_found, cadence_status = cadence.detect_array_with_status(bgr)
                # Existing cadence logic requires two axes, an independently
                # confirmed grid cadence, a unique phase and spatial overlap.
                # Never include these *suggestions* in persisted pv_modules.
                cadence_proposals += len(cadence_found)
                cadence_frames += bool(cadence_found)
                if not cadence_found:
                    if cadence_status == "independent_image_support_required":
                        no_support += 1
                    elif cadence_status in (
                        "two_grid_families_required", "cadence_not_confirmed",
                    ):
                        no_grid += 1
                    elif cadence_status in (
                        "unresolved_cadence_phase", "invalid_resolved_phase",
                    ):
                        no_phase += 1
                    else:
                        other += 1
                analyzed += 1
            except (ValueError, TypeError, cv2.error):
                errors += 1
            finally:
                del bgr
        if on_progress is not None:
            on_progress(checked, sample_size, errors)
        if cancelled():
            raise ModuleSampleCancelled()
    final = capture_offline_processing_inventory(database, project_id)
    return ModuleSampleResult(
        available_rgb=initial.rgb_frames, sample_size=sample_size,
        checked=checked, analyzed=analyzed, issues=errors, unverified=missing,
        structural_proposals=grids, visual_proposals=visuals,
        overlapping_proposals=overlaps, frames_with_overlap=supported_frames,
        changed_inputs=final.fingerprint != initial.fingerprint,
        cadence_proposals=cadence_proposals,
        cadence_frames_with_proposals=cadence_frames,
        cadence_rejected_no_support=no_support,
        cadence_rejected_grid=no_grid,
        cadence_rejected_phase=no_phase,
        cadence_rejected_other=other,
    )
