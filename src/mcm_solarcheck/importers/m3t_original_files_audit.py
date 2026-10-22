"""Read-only DJI M3T unpacked-file validation, shared with permanent staging."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from PIL import Image
from mcm_solarcheck.importers.m3t_original_zip_staging import MAX_TOTAL_STAGED_BYTES

DJI_ORIGINAL = re.compile(r"DJI_(\d{14})_(\d{4})_([TV])\.JPG\Z", re.IGNORECASE)
MAX_FILE_BYTES = {"T": 30_000_000, "V": 40_000_000}
MAX_FILES = 15_000


@dataclass(frozen=True)
class OriginalFileIdentity:
    path: Path
    name: str
    sequence: str
    exposure: str
    modality: str
    size_bytes: int


@dataclass(frozen=True)
class OriginalFilesAudit:
    files: tuple[OriginalFileIdentity, ...]
    matched_pairs: int
    thermal_only: int
    rgb_only: int

    @property
    def thermal_images(self) -> int:
        return sum(item.modality == "T" for item in self.files)

    @property
    def rgb_images(self) -> int:
        return sum(item.modality == "V" for item in self.files)

    def aggregate(self) -> dict:
        """No paths, timestamps, names, GPS, or original bytes."""
        return {
            "thermal_images": self.thermal_images,
            "rgb_images": self.rgb_images,
            "filename_timestamp_matched_pairs": self.matched_pairs,
            "thermal_without_rgb": self.thermal_only,
            "rgb_without_thermal": self.rgb_only,
            "radiometric_celsius_validated": False,
            "physical_module_identity_validated": False,
            "report_or_training_approved": False,
        }


def audit_original_m3t_files(original_files, *, should_cancel=None) -> OriginalFilesAudit:
    """Inspect only explicitly selected originals, with zero database/file writes.

    Filename/time pairing is not physical registration. Thermal-only
    selections and multiple source directories are allowed.
    """
    if not isinstance(original_files, (list, tuple)):
        raise TypeError("An explicitly selected sequence of files is required")
    if not 1 <= len(original_files) <= MAX_FILES:
        raise ValueError("Select between 1 and 15000 DJI originals")
    checked = []
    seen_names: set[str] = set()
    seen_keys: set[tuple[str, str]] = set()
    timestamps: dict[str, dict[str, str]] = {}
    total = 0
    for selected in original_files:
        if should_cancel is not None and should_cancel():
            raise InterruptedError("Original-file inspection cancelled")
        path = Path(selected)
        if (not path.is_absolute() or path.is_symlink() or not path.is_file()
                or path.parent.is_symlink()):
            raise PermissionError("Explicit local regular image file required")
        match = DJI_ORIGINAL.fullmatch(path.name)
        if match is None:
            raise ValueError("Unexpected DJI original image filename")
        stamp, counter, kind = match.group(1), match.group(2), match.group(3).upper()
        # The existing importers scan canonical '*_T.JPG'/'*_V.JPG' names.
        # Reject noncanonical case instead of silently omitting frames.
        if path.name != f"DJI_{stamp}_{counter}_{kind}.JPG":
            raise ValueError("Selected DJI filename is not canonical for importer")
        datetime.strptime(stamp, "%Y%m%d%H%M%S")
        if path.name.casefold() in seen_names or (kind, counter) in seen_keys:
            raise ValueError("Duplicated original DJI image identity")
        seen_names.add(path.name.casefold())
        seen_keys.add((kind, counter))
        size = path.stat().st_size
        if not 0 < size <= MAX_FILE_BYTES[kind]:
            raise ValueError("Invalid DJI original byte size")
        total += size
        if total > MAX_TOTAL_STAGED_BYTES:
            raise ValueError("Selected original files exceed resource limit")
        with Image.open(path) as image:
            if image.format not in ("MPO", "JPEG"):
                raise ValueError("Unsupported DJI original container")
            if image.size != ((640, 512) if kind == "T" else (4000, 3000)):
                raise ValueError("DJI original sensor size differs")
            tags = image.getexif()
            date = f"{stamp[:4]}:{stamp[4:6]}:{stamp[6:8]} {stamp[8:10]}:{stamp[10:12]}:{stamp[12:14]}"
            if tags.get(271) != "DJI" or tags.get(272) != "M3T" or tags.get(306) != date:
                raise ValueError("DJI EXIF identity disagrees with filename")
        timestamps.setdefault(counter, {})[kind] = stamp
        checked.append(OriginalFileIdentity(path, path.name, counter, stamp, kind, size))
    if any(len(p) == 2 and p["T"] != p["V"] for p in timestamps.values()):
        raise ValueError("Thermal/RGB exposure times conflict")
    return OriginalFilesAudit(
        tuple(checked),
        sum(len(p) == 2 for p in timestamps.values()),
        sum("T" in p and "V" not in p for p in timestamps.values()),
        sum("V" in p and "T" not in p for p in timestamps.values()),
    )
