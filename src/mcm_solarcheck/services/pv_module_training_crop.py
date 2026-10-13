"""Explicit offline module-only RGB crop export with no copied source metadata."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PIL import Image

from mcm_solarcheck.services.pv_training_image_quality import inspect_training_image


@dataclass(frozen=True)
class ModuleCropReview:
    consent_reference: str
    reviewer_reference: str
    module_only_confirmed: bool
    no_identifying_context_confirmed: bool
    crop_xyxy: tuple[float, float, float, float]
    source_is_rgb: bool = True

    def __post_init__(self) -> None:
        if not self.consent_reference.strip() or not self.reviewer_reference.strip():
            raise PermissionError("affirmative consent and human reviewer evidence required")
        if not self.module_only_confirmed or not self.no_identifying_context_confirmed or not self.source_is_rgb:
            raise PermissionError("reviewed RGB module-only image required")
        from math import isfinite
        v = self.crop_xyxy
        if len(v) != 4 or not all(isinstance(x, (float, int)) and isfinite(x) for x in v):
            raise ValueError("normalized crop required")
        if not (0 <= v[0] < v[2] <= 1 and 0 <= v[1] < v[3] <= 1):
            raise ValueError("invalid normalized crop")


@dataclass(frozen=True)
class ModuleCropExport:
    output_path: Path
    width: int
    height: int
    status: str = "privacy_reviewed_not_proven_anonymous"


def export_reviewed_rgb_module_crop(
    source: Path, destination_directory: Path, review: ModuleCropReview,
    *, max_output_pixels: int = 8_000_000,
) -> ModuleCropExport:
    """Write a newly encoded RGB PNG; never copy EXIF, XMP, GPS or filename."""
    if not isinstance(review, ModuleCropReview):
        raise PermissionError("review required")
    if type(max_output_pixels) is not int or not 1 <= max_output_pixels <= 50_000_000:
        raise ValueError("invalid output pixel limit")
    source = Path(source)
    destination_directory = Path(destination_directory)
    if not destination_directory.is_dir() or destination_directory.is_symlink():
        raise ValueError("regular preexisting destination directory required")
    if source.resolve(strict=True) == destination_directory.resolve(strict=True):
        raise ValueError("source and destination cannot match")
    inspect_training_image(source)
    with Image.open(source) as image:
        if image.format not in ("JPEG", "PNG"):
            raise ValueError("RGB JPEG or PNG required")
        if image.mode not in ("RGB", "RGBA"):
            raise ValueError("radiometric or non-RGB imagery is not supported")
        width, height = image.size
        x1, y1, x2, y2 = review.crop_xyxy
        bounds = (int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height))
        cw, ch = bounds[2] - bounds[0], bounds[3] - bounds[1]
        if min(cw, ch) < 32 or cw * ch > max_output_pixels:
            raise ValueError("crop outside safe size limits")
        # Create a new pixel-only image, excluding source info and EXIF/XMP chunks.
        pixels = image.crop(bounds).convert("RGB")
        clean = Image.new("RGB", pixels.size)
        clean.paste(pixels)
        output = destination_directory / (uuid4().hex + ".png")
        with output.open("xb") as handle:
            clean.save(handle, format="PNG")
    return ModuleCropExport(output, cw, ch)
