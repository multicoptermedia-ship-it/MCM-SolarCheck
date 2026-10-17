"""Offline DJI flight ZIP preflight; never extracts or uploads original imagery."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from zipfile import ZipFile, BadZipFile

_NAME = re.compile(r"DJI_(\d{14})_(\d{4})_([TV])\.JPG", re.IGNORECASE)


@dataclass(frozen=True)
class FlightZipPreflight:
    rgb_count: int
    thermal_count: int
    paired_count: int
    unpaired_ids: tuple[str, ...]
    mismatched_timestamps: tuple[str, ...]
    diagnostics: tuple[str, ...]

    @property
    def ready_for_geometry(self) -> bool:
        return False  # Filename pairing cannot establish surveyed roof geometry.


def inspect_dji_flight_zip(path, *, max_entries=10000, max_uncompressed_bytes=10_000_000_000):
    """Inspect only ZIP directory entries and DJI filenames, not EXIF or radiometry."""
    frames = {}
    diagnostics = []
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > max_entries or sum(x.file_size for x in members) > max_uncompressed_bytes:
                raise ValueError("flight archive exceeds preflight limits")
            for item in members:
                if item.is_dir():
                    continue
                name = PurePosixPath(item.filename)
                if name.is_absolute() or ".." in name.parts or chr(92) in item.filename or re.match(r"^[A-Za-z]:", item.filename):
                    raise ValueError("unsafe archive member path")
                match = _NAME.fullmatch(name.name)
                if not match:
                    diagnostics.append("non-DJI or unsupported archive entry")
                    continue
                timestamp, number, modality = match.groups()
                key = (number, modality.upper())
                if key in frames:
                    raise ValueError("duplicate DJI frame identifier and modality")
                frames[key] = timestamp
    except BadZipFile as error:
        raise ValueError("invalid flight ZIP archive") from error
    ids = {number for number, _ in frames}
    missing = tuple(sorted(number for number in ids if (number, "T") not in frames or (number, "V") not in frames))
    mismatch = tuple(sorted(number for number in ids if (number, "T") in frames and (number, "V") in frames and frames[(number, "T")] != frames[(number, "V")]))
    if missing:
        diagnostics.append("unpaired RGB/thermal frame IDs")
    if mismatch:
        diagnostics.append("RGB/thermal timestamps differ")
    diagnostics.append("camera calibration and independently surveyed roof plane still required")
    diagnostics.append("thermal JPEG palette is not verified radiometric data")
    return FlightZipPreflight(
        sum(mode == "V" for _, mode in frames),
        sum(mode == "T" for _, mode in frames),
        sum((number, "T") in frames and (number, "V") in frames and number not in mismatch for number in ids),
        missing, mismatch, tuple(dict.fromkeys(diagnostics)),
    )
