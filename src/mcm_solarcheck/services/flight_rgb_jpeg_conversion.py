"""Conservative JPEG-to-window-source conversion.

The JPEG decoder still allocates a full RGB frame. This converter rejects
images above a strict decoded-pixel budget; it is NOT streaming JPEG decoding.
"""
import os
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np

from mcm_solarcheck.services.flight_rgb_jpeg_header import jpeg_dimensions


def convert_jpeg_to_rgb_array(source, destination, *, max_pixels=12_000_000,
                              max_source_bytes=80_000_000,
                              max_output_bytes=40_000_000):
    """Publish a derived .npy source without modifying JPEG or replacing output."""
    source, destination = Path(source), Path(destination)
    if (source.is_symlink() or not source.is_file()
            or source.suffix.lower() not in (".jpg", ".jpeg")
            or destination.is_symlink() or destination.exists()
            or destination.suffix.lower() != ".npy"
            or not destination.parent.is_dir()):
        raise ValueError("regular JPEG and new .npy destination required")
    if (type(max_pixels) is not int or max_pixels < 1
            or type(max_source_bytes) is not int or max_source_bytes < 1
            or type(max_output_bytes) is not int or max_output_bytes < 1):
        raise ValueError("invalid conversion limits")
    if source.stat().st_size > max_source_bytes:
        raise ValueError("JPEG exceeds source byte budget")
    expected_width, expected_height = jpeg_dimensions(source)
    if expected_width * expected_height > max_pixels:
        raise ValueError("JPEG header exceeds pixel budget before decode")
    encoded = source.read_bytes()
    if len(encoded) > max_source_bytes:
        raise ValueError("JPEG exceeds source byte budget")
    image = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("unreadable RGB JPEG")
    height, width = image.shape[:2]
    if (height, width) != (expected_height, expected_width):
        raise ValueError("JPEG decoded dimensions differ from header")
    if height * width > max_pixels:
        raise ValueError("decoded JPEG exceeds pixel budget")
    estimated_output_bytes = height * width * 3 + 4096
    if estimated_output_bytes > max_output_bytes:
        raise ValueError("RGB working array exceeds output byte budget")
    if shutil.disk_usage(destination.parent).free < estimated_output_bytes:
        raise ValueError("insufficient free disk space for RGB working array")
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".rgb-array-",
                                         suffix=".tmp", delete=False) as handle:
            staged = Path(handle.name)
            np.save(handle, rgb, allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(staged, destination, follow_symlinks=False)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    return {"width": width, "height": height, "decoded_pixels": width * height,
            "source_modified": False, "jpeg_region_decoding": False}
