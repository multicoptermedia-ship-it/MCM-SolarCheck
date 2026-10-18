"""Discover DJI RGB images in a local folder without manual file marking.

This first vertical slice deliberately refuses flights beyond four frames:
the existing projective preview cannot yet cover a whole flight.
"""
from __future__ import annotations

from pathlib import Path
import re

from mcm_solarcheck.services.flight_visual_files import preview_rgb_files

_DJI_RGB = re.compile(r"DJI_\d{14}_(\d{4})_V\.(?:JPG|JPEG|PNG)", re.IGNORECASE)


def discover_rgb_images(directory):
    folder = Path(directory)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("existing local image folder required")
    frames = []
    for path in folder.iterdir():
        if path.is_symlink() or not path.is_file():
            continue
        match = _DJI_RGB.fullmatch(path.name)
        if match:
            frames.append((match.group(1), path))
    frames.sort(key=lambda item: (item[0], item[1].name))
    ids = [item[0] for item in frames]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate DJI RGB frame IDs")
    if not 3 <= len(frames) <= 4:
        raise ValueError(
            f"found {len(frames)} DJI RGB images; automatic preview currently supports exactly 3-4; "
            "whole-flight processing is not yet available"
        )
    return tuple(path for _, path in frames)


def preview_rgb_folder(directory, output_png, quality_json):
    """Discover, order, then immediately process all supported RGB frames."""
    return preview_rgb_files(discover_rgb_images(directory), output_png, quality_json)
