"""Materialize report image crops while preserving source-frame provenance."""
from __future__ import annotations
from pathlib import Path
from PIL import Image
from .image_crop import CropBox


def materialize_crop(source: str | Path, destination: str | Path, box: CropBox) -> Path:
    """Crop a source image to a validated box; never resize or infer coordinates."""
    source=Path(source); destination=Path(destination)
    if not source.is_file(): raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(source) as image:
        width,height=image.size
        if box.right>width or box.bottom>height:
            raise ValueError("crop box exceeds source image dimensions")
        cropped=image.crop((box.left,box.top,box.right,box.bottom))
        cropped.save(destination)
    return destination
