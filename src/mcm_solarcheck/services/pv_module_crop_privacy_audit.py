"""Validate metadata-free training crop files without claiming legal anonymity."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from mcm_solarcheck.services.pv_training_image_quality import inspect_training_image


FORBIDDEN_PNG_CHUNKS = (b"eXIf", b"iTXt", b"tEXt", b"zTXt")


def audit_module_training_crop(path: Path) -> bool:
    """Reject metadata-bearing PNGs; cannot detect identifiers inside pixels."""
    quality = inspect_training_image(path)
    if quality.image_format != "PNG":
        raise ValueError("fresh PNG training crop required")
    with Image.open(path) as image:
        if image.mode != "RGB" or image.info:
            raise ValueError("unexpected image mode or metadata")
    data = Path(path).read_bytes()
    if any(marker in data for marker in FORBIDDEN_PNG_CHUNKS):
        raise ValueError("potential embedded PNG metadata")
    return True
