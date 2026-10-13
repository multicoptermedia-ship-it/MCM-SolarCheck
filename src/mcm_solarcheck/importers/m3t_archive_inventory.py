"""Privacy-safe DJI M3T ZIP inventory; no image extraction or transmission."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from zipfile import ZipFile

_PATTERN = re.compile(r"^DJI_\d{14}_(\d{4})_([TV])\.JPG$", re.IGNORECASE)


@dataclass(frozen=True)
class M3TArchiveInventory:
    paired_sequences: tuple[str, ...]
    thermal_only_sequences: tuple[str, ...]
    rgb_only_sequences: tuple[str, ...]
    thermal_files: int
    rgb_files: int


def _sequences(archive: str | Path, expected: str) -> set[str]:
    found: set[str] = set()
    with ZipFile(archive) as zf:
        for entry in zf.infolist():
            if entry.is_dir():
                continue
            if "/" in entry.filename or "\\" in entry.filename:
                raise ValueError("nested or unsafe archive path")
            match = _PATTERN.fullmatch(entry.filename)
            if not match or match.group(2).upper() != expected:
                raise ValueError("unexpected DJI image filename")
            if match.group(1) in found:
                raise ValueError("duplicate DJI image sequence")
            found.add(match.group(1))
    return found


def inspect_m3t_archives(thermal_zip: str | Path, rgb_zip: str | Path) -> M3TArchiveInventory:
    thermal = _sequences(thermal_zip, "T")
    rgb = _sequences(rgb_zip, "V")
    return M3TArchiveInventory(
        paired_sequences=tuple(sorted(thermal & rgb)),
        thermal_only_sequences=tuple(sorted(thermal - rgb)),
        rgb_only_sequences=tuple(sorted(rgb - thermal)),
        thermal_files=len(thermal),
        rgb_files=len(rgb),
    )
