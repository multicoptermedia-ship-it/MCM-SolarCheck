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


def main(argv=None):
    """Offline CLI for a native-resolution RGB segment, not an orthophoto."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", action="append", required=True,
                        help="RGB image in capture order (repeat 3-4 times)")
    parser.add_argument("--output", required=True, help="new PNG destination")
    parser.add_argument("--quality-json", required=True, help="new JSON destination")
    parser.add_argument("--max-canvas-pixels", type=int, default=80_000_000)
    args = parser.parse_args(argv)
    compose_native_rgb_segment(
        args.image, args.output, args.quality_json,
        max_canvas_pixels=args.max_canvas_pixels,
    )
    print("Native-pixel nonmetric RGB segment written; NOT a surveyed orthophoto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
