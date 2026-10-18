"""Write a bounded nonmetric RGB preview and explicit quality metadata."""
import json
from pathlib import Path

import cv2

from mcm_solarcheck.services.flight_rgb_segment_render import render_rgb_segment


def save_rgb_segment_preview(segment, frames, png_path, quality_path, *,
                             max_pixels=12_000_000):
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
    ok, encoded = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ValueError("RGB preview PNG encoding failed")
    with png.open("xb") as output:
        output.write(encoded.tobytes())
    try:
        with quality.open("x", encoding="utf-8") as output:
            json.dump(metadata, output, ensure_ascii=False, indent=2)
            output.write("\n")
    except Exception:
        png.unlink(missing_ok=True)
        raise
    return metadata
