"""Native-resolution RGB composition for a bounded 3-4 frame flight segment.

The projective image is nonmetric; this is not a surveyed orthophoto.
"""
from pathlib import Path

from mcm_solarcheck.services.flight_visual_files import preview_rgb_files


def compose_native_rgb_segment(image_paths, output_png, quality_json,
                               *, max_canvas_pixels=80_000_000):
    """Render from original pixels, refusing unbounded canvases."""
    if type(max_canvas_pixels) is not int or max_canvas_pixels < 1:
        raise ValueError("invalid native canvas pixel limit")
    return preview_rgb_files(
        image_paths, Path(output_png), Path(quality_json),
        max_side=None, max_canvas_pixels=max_canvas_pixels,
    )
