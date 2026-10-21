"""Privacy-preserving original DJI M3T ZIP audit for non-contiguous archives.

All output is aggregate metadata; never print timestamps, GPS, file paths,
original images or customer-specific EXIF. No extraction or database writes.
Pair identity requires BOTH unique 4-digit counters AND identical filename
exposure timestamps (not sequence-number-only matching).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
import re
import stat
from zipfile import ZipFile

from PIL import Image

_NAME = re.compile(r"DJI_(\d{14})_(\d{4})_([TV])\.JPG\Z", re.IGNORECASE)
_MAX_ENTRIES = 15_000
_MAX_ARCHIVE_BYTES = 35_000_000_000
_MAX_THERMAL_BYTES = 30_000_000
_MAX_RGB_BYTES = 40_000_000


@dataclass(frozen=True)
class OriginalM3TFrame:
    sequence: str
    exposure: str
    name: str
    size_bytes: int
    modality: str


@dataclass(frozen=True)
class OriginalM3TArchiveAudit:
    thermal: tuple[OriginalM3TFrame, ...]
    rgb: tuple[OriginalM3TFrame, ...]
    paired_sequences: tuple[str, ...]
    thermal_only_sequences: tuple[str, ...]
    rgb_only_sequences: tuple[str, ...]
    mismatched_timestamp_sequences: tuple[str, ...]

    def summary(self) -> dict:
        """No physical locations, captured timestamps or original names."""
        return {
            "thermal_images": len(self.thermal),
            "rgb_images": len(self.rgb),
            "confirmed_pairs": len(self.paired_sequences),
            "thermal_without_rgb": len(self.thermal_only_sequences),
            "rgb_without_thermal": len(self.rgb_only_sequences),
            "sequence_timestamp_conflicts": len(self.mismatched_timestamp_sequences),
            "all_pairs_consistent": not self.mismatched_timestamp_sequences
                                    and not self.rgb_only_sequences,
            "radiometric_celsius_validated": False,
            "source_files_untouched": True,
            "research_or_import_use_requires_separate_explicit_approval": True,
        }


def _scan_archive(path: Path, suffix: str, *, inspect_images: bool) -> tuple[OriginalM3TFrame, ...]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise PermissionError("absolute regular local ZIP file required")
    result: dict[str, OriginalM3TFrame] = {}
    combined_size = 0
    with ZipFile(path) as archive:
        members = archive.infolist()
        if not 1 <= len(members) <= _MAX_ENTRIES:
            raise ValueError("empty or oversized M3T ZIP directory")
        for member in members:
            if member.is_dir():
                raise ValueError("DJI ZIP must contain files only")
            name = member.filename
            if "/" in name or "\\" in name:
                raise PermissionError("nested or unsafe archive member")
            match = _NAME.fullmatch(name)
            if match is None or match.group(3).upper() != suffix:
                raise ValueError("unexpected DJI image filename or modality")
            stamp, counter = match.group(1), match.group(2)
            try:
                datetime.strptime(stamp, "%Y%m%d%H%M%S")
            except ValueError as exc:
                raise ValueError("invalid DJI filename timestamp") from exc
            kind = stat.S_IFMT(member.external_attr >> 16)
            if kind not in (0, stat.S_IFREG):
                raise PermissionError("ZIP symlink or special member rejected")
            size_limit = _MAX_THERMAL_BYTES if suffix == "T" else _MAX_RGB_BYTES
            combined_size += member.file_size
            if (not 0 < member.file_size <= size_limit
                    or combined_size > _MAX_ARCHIVE_BYTES
                    or member.compress_size > size_limit):
                raise ValueError("M3T image archive size limit exceeded")
            if counter in result:
                raise ValueError("duplicate DJI sequence in archive")
            if inspect_images:
                with archive.open(member) as stream:
                    raw = stream.read(size_limit + 1)
                if len(raw) != member.file_size or len(raw) > size_limit:
                    raise ValueError("truncated or oversized original DJI image")
                try:
                    with Image.open(BytesIO(raw)) as image:
                        # Pillow returns MPO for real original DJI M3T photos;
                        # compatible standalone JPEG is accepted for controlled tests.
                        if image.format not in ("MPO", "JPEG"):
                            raise ValueError("unsupported DJI image container")
                        expected = (640, 512) if suffix == "T" else (4000, 3000)
                        if image.size != expected:
                            raise ValueError("unexpected DJI sensor raster")
                        tags = image.getexif()
                        if tags.get(271) != "DJI" or tags.get(272) != "M3T":
                            raise ValueError("unknown DJI camera model")
                        if tags.get(306) != (
                            f"{stamp[:4]}:{stamp[4:6]}:{stamp[6:8]} "
                            f"{stamp[8:10]}:{stamp[10:12]}:{stamp[12:14]}"
                        ):
                            raise ValueError("DJI camera EXIF and filename times differ")
                except (OSError, SyntaxError) as exc:
                    raise ValueError("unreadable DJI image metadata") from exc
            result[counter] = OriginalM3TFrame(
                counter, stamp, name, member.file_size, suffix,
            )
    return tuple(result[x] for x in sorted(result))


def audit_original_m3t_archives(
    thermal_zip: str | Path, rgb_zip: str | Path, *,
    inspect_images: bool = True,
) -> OriginalM3TArchiveAudit:
    thermal = _scan_archive(Path(thermal_zip), "T", inspect_images=inspect_images)
    rgb = _scan_archive(Path(rgb_zip), "V", inspect_images=inspect_images)
    by_thermal = {x.sequence: x for x in thermal}
    by_rgb = {x.sequence: x for x in rgb}
    shared = set(by_thermal) & set(by_rgb)
    mismatches = tuple(sorted(
        key for key in shared
        if by_thermal[key].exposure != by_rgb[key].exposure
    ))
    pairs = tuple(sorted(shared - set(mismatches)))
    return OriginalM3TArchiveAudit(
        thermal, rgb, pairs,
        tuple(sorted(set(by_thermal) - set(by_rgb))),
        tuple(sorted(set(by_rgb) - set(by_thermal))),
        mismatches,
    )
