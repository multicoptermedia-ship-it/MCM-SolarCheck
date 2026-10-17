"""Bridge imported frames to native surveyed-planar orthophoto inputs.

Uses the existing importer output; no EXIF reread or pose-to-roof inference.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np

from mcm_solarcheck.domain.models import ImageFrame, ThermalFrame
from mcm_solarcheck.services.orthophoto_planar_rectification import SurveyedFrame


@dataclass(frozen=True)
class ImportedSurveyedControl:
    frame_id: str
    pixel_points: tuple[tuple[float, float], ...]
    world_points: tuple[tuple[float, float], ...]
    independently_surveyed: bool = False


def surveyed_frames_from_import(
    frames: tuple[ImageFrame, ...],
    controls: tuple[ImportedSurveyedControl, ...],
    *,
    thermal: bool = False,
) -> tuple[SurveyedFrame, ...]:
    """Prepare verified planar frames without inventing survey geometry."""
    if not frames:
        raise ValueError("at least one imported photograph required")
    if len(frames) != len(controls):
        raise ValueError("each imported frame needs matching surveyed controls")
    if any(not isinstance(item, ImageFrame) for item in frames):
        raise TypeError("imported ImageFrame required")
    ids = [frame.frame_id for frame in frames]
    if any(not isinstance(value, str) or not value.strip() for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("unique nonempty imported frame IDs required")
    by_id = {}
    for control in controls:
        if not isinstance(control, ImportedSurveyedControl) or not control.frame_id or control.frame_id in by_id:
            raise ValueError("unique surveyed control records required")
        if control.independently_surveyed is not True:
            raise ValueError("independently surveyed controls required")
        by_id[control.frame_id] = control
    if set(by_id) != set(ids):
        raise ValueError("surveyed control IDs must match imported frame IDs")
    result = []
    for frame in frames:
        if isinstance(frame, ThermalFrame) != thermal:
            raise ValueError("RGB and thermal source frames must be processed separately")
        path = Path(frame.source_file)
        if not path.is_file() or path.is_symlink():
            raise ValueError("imported source image must be an existing local file")
        if type(frame.width) is not int or type(frame.height) is not int or frame.width <= 0 or frame.height <= 0:
            raise ValueError("imported image dimensions required")
        control = by_id[frame.frame_id]
        pixel = np.asarray(control.pixel_points, dtype=np.float64)
        world = np.asarray(control.world_points, dtype=np.float64)
        if pixel.ndim != 2 or world.shape != pixel.shape or pixel.shape[1:] != (2,) or len(pixel) < 4:
            raise ValueError("at least four paired planar control points required")
        if not np.isfinite(pixel).all() or not np.isfinite(world).all():
            raise ValueError("finite surveyed controls required")
        if np.any(pixel < 0) or np.any(pixel[:, 0] >= frame.width) or np.any(pixel[:, 1] >= frame.height):
            raise ValueError("control pixels outside imported image")
        result.append(SurveyedFrame(path, control.pixel_points, control.world_points, controls_surveyed=True))
    return tuple(result)
