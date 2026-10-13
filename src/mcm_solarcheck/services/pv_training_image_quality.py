"""Bounded read-only image integrity checks for local PV training sets."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True)
class TrainingImageQuality:
    width: int
    height: int
    image_format: str
    file_bytes: int


def inspect_training_image(
    path: Path, *, max_file_bytes: int = 30_000_000,
    max_pixels: int = 50_000_000, min_dimension: int = 32,
) -> TrainingImageQuality:
    if type(max_file_bytes) is not int or max_file_bytes < 1:
        raise ValueError("invalid file byte limit")
    if type(max_pixels) is not int or max_pixels < 1:
        raise ValueError("invalid pixel limit")
    if type(min_dimension) is not int or min_dimension < 1:
        raise ValueError("invalid minimum dimension")
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular image file required")
    size = path.stat().st_size
    if not 0 < size <= max_file_bytes:
        raise ValueError("image exceeds byte limit or is empty")
    try:
        with Image.open(path) as image:
            fmt = image.format
            width, height = image.size
            if fmt not in ("JPEG", "PNG"):
                raise ValueError("only JPEG and PNG training images accepted")
            if min(width, height) < min_dimension or width * height > max_pixels:
                raise ValueError("image dimensions outside allowed bounds")
            image.load()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("invalid or unsafe image content") from exc
    return TrainingImageQuality(width, height, fmt, size)
