"""Write a bounded nonmetric RGB preview and explicit quality metadata."""
import json
import tempfile
from pathlib import Path

import cv2

from mcm_solarcheck.services.flight_rgb_segment_render import render_rgb_segment


def save_rgb_segment_preview(segment, frames, png_path, quality_path, *,
                             max_pixels=12_000_000, extra_metadata=None):
    png = Path(png_path)
    quality = Path(quality_path)
    if (png.suffix.lower() != ".png" or quality.suffix.lower() != ".json"
            or png == quality or png.exists() or quality.exists()
            or not png.parent.is_dir() or not quality.parent.is_dir()):
        raise ValueError("new PNG and JSON output paths required")
    image, metadata = render_rgb_segment(segment, frames, max_pixels=max_pixels)
    metadata.update(processing_kind="nonmetric_rgb_segment_preview",
                    metric_orthophoto_verified=False,
                    full_resolution_sources_modified=False,
                    temperature_calibrated=False)
    if extra_metadata is not None:
        if not isinstance(extra_metadata, dict):
            raise ValueError("invalid preview metadata")
        metadata.update(extra_metadata)
    ok, encoded = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ValueError("RGB preview PNG encoding failed")
    # Stage complete bytes before publishing either file.
    staged = []
    try:
        for destination, payload in (
            (png, encoded.tobytes()),
            (quality, (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")),
        ):
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, prefix=".rgb-preview-",
                suffix=".tmp", delete=False
            ) as output:
                staged.append(Path(output.name))
                output.write(payload)
        # Atomically publish each complete file; never replace an existing target.
        # A hard link to the staged inode provides exclusive creation on the same FS.
        import os
        os.link(staged[0], png, follow_symlinks=False)
        try:
            os.link(staged[1], quality, follow_symlinks=False)
        except Exception:
            png.unlink(missing_ok=True)
            raise
    finally:
        for temporary in staged:
            temporary.unlink(missing_ok=True)
    return metadata
