"""Read-only JPEG/EXIF readiness scan for local DJI flight archives.

This is a format diagnostic, not an independent calibration or roof survey.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile

from mcm_solarcheck.services.flight_zip_preflight import inspect_dji_flight_zip


@dataclass(frozen=True)
class FlightImageReadiness:
    rgb_images: int
    thermal_images: int
    rgb_dimensions: tuple[tuple[int, int], ...]
    thermal_dimensions: tuple[tuple[int, int], ...]
    thermal_palette_images: int
    diagnostics: tuple[str, ...]

    @property
    def ready_for_metric_orthophoto(self) -> bool:
        return False  # No surveyed plane, calibrated cameras or ENU frames from JPEG alone.


def inspect_flight_image_readiness(path, *, max_image_bytes=80_000_000):
    """Inspect JPEG headers/EXIF locally without extracting image files."""
    from PIL import Image, UnidentifiedImageError

    preflight = inspect_dji_flight_zip(path)
    counts = {"V": 0, "T": 0}
    sizes = {"V": set(), "T": set()}
    palettes = 0
    with ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            name = PurePosixPath(member.filename).name
            import re
            match = re.fullmatch(r"DJI_\\d{14}_\\d{4}_([TV])\\.JPG", name, re.IGNORECASE)
            if match is None:
                continue
            mode = match.group(1).upper()
            if member.file_size > max_image_bytes:
                raise ValueError("JPEG exceeds local image size limit")
            try:
                with archive.open(member) as stream:
                    payload = stream.read(max_image_bytes + 1)
                if len(payload) > max_image_bytes:
                    raise ValueError("JPEG exceeds local image size limit")
                with Image.open(BytesIO(payload)) as image:
                    if image.format != "JPEG":
                        raise ValueError("DJI image entry is not JPEG")
                    dimensions = image.size
                    bands = image.getbands()
                    image.getexif()  # Confirm EXIF is readable; no coordinates are exposed.
                    if mode == "T" and len(bands) >= 3:
                        palettes += 1
            except (UnidentifiedImageError, OSError) as error:
                raise ValueError("unreadable DJI JPEG") from error
            counts[mode] += 1
            sizes[mode].add(dimensions)
    notes = list(preflight.diagnostics)
    if palettes:
        notes.append("thermal JPEG is multichannel; cannot treat it as raw single-band temperature data")
    if len(sizes["V"]) > 1 or len(sizes["T"]) > 1:
        notes.append("inconsistent image dimensions within a modality")
    return FlightImageReadiness(
        counts["V"], counts["T"], tuple(sorted(sizes["V"])),
        tuple(sorted(sizes["T"])), palettes, tuple(dict.fromkeys(notes)),
    )
