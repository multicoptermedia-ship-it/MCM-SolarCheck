"""Local DJI-folder RGB segment preview from a completed registration result."""
from pathlib import Path

import cv2
import numpy as np

from mcm_solarcheck.services.flight_inventory import scan_flight
from mcm_solarcheck.services.flight_rgb_segment_export import save_rgb_segment_preview


def export_flight_rgb_segment(folder, registration, segment_index, png_path, quality_path,
                              *, max_side=800, max_frames=8,
                              max_image_bytes=80_000_000, max_pixels=12_000_000,
                              sample_long_segments=False):
    """Render one bounded working-resolution segment, never overwrite originals."""
    if (type(segment_index) is not int or segment_index < 0
            or type(max_side) is not int or max_side < 128
            or type(max_frames) is not int or max_frames < 1
            or type(max_image_bytes) is not int or max_image_bytes < 1):
        raise ValueError("invalid RGB segment export configuration")
    segments = registration["nonmetric_geometry"]["segments"]
    if segment_index >= len(segments):
        raise ValueError("RGB segment index out of range")
    segment = segments[segment_index]
    keys = list(segment["frames"])
    if len(keys) > max_frames and not sample_long_segments:
        raise ValueError("RGB segment exceeds working frame limit")
    if len(keys) > max_frames:
        # Deterministic coverage; this is a sample, never a complete mosaic.
        selected = [keys[i * (len(keys) - 1) // (max_frames - 1)]
                    for i in range(max_frames)] if max_frames > 1 else [keys[0]]
    else:
        selected = keys
    captures, _ = scan_flight(folder)
    rgb_paths = {key: rgb for key, rgb, _ in captures}
    frames = {}
    for key in selected:
        path = rgb_paths.get(key)
        if path is None or path.is_symlink() or not path.is_file():
            raise ValueError("missing regular RGB source: " + key)
        if path.stat().st_size > max_image_bytes:
            raise ValueError("RGB source exceeds byte limit")
        data = path.read_bytes()
        if len(data) > max_image_bytes:
            raise ValueError("RGB source exceeds byte limit")
        decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError("unreadable RGB source: " + key)
        height, width = decoded.shape[:2]
        scale = min(1.0, max_side / max(width, height))
        if scale < 1.0:
            decoded = cv2.resize(decoded, (max(1, round(width * scale)),
                                            max(1, round(height * scale))))
        frames[key] = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
    preview_segment = dict(segment, frames={key: segment["frames"][key] for key in selected})
    metadata = save_rgb_segment_preview(preview_segment, frames, png_path, quality_path,
                                         max_pixels=max_pixels)
    metadata["working_max_side"] = max_side
    metadata["source_frame_count"] = len(keys)
    metadata["preview_frame_count"] = len(selected)
    metadata["preview_incomplete"] = len(selected) < len(keys)
    metadata["preview_frame_keys"] = selected
    return metadata
