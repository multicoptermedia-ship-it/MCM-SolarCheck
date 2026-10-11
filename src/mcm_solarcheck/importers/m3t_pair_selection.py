"""Local-only, fail-closed selection of DJI M3T matched ZIP frames."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from zipfile import ZipFile

_RE = re.compile(r"^DJI_\d{14}_(\d{4})_([TV])\.JPG$", re.IGNORECASE)


@dataclass(frozen=True)
class MatchedM3TSelection:
    sequences: tuple[str, ...]
    thermal_names: tuple[str, ...]
    rgb_names: tuple[str, ...]


def select_m3t_pairs(thermal_zip: str | Path, rgb_zip: str | Path, *, count: int = 29) -> MatchedM3TSelection:
    if count < 1:
        raise ValueError("count must be positive")

    def scan(path: str | Path, modality: str) -> dict[str, str]:
        names: dict[str, str] = {}
        with ZipFile(path) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                if "/" in item.filename or "\\" in item.filename:
                    raise ValueError("unsafe archive member")
                match = _RE.fullmatch(item.filename)
                if not match or match.group(2).upper() != modality:
                    raise ValueError("unexpected archive member")
                if match.group(1) in names:
                    raise ValueError("duplicate sequence")
                names[match.group(1)] = item.filename
        return names

    thermal = scan(thermal_zip, "T")
    rgb = scan(rgb_zip, "V")
    sequences = tuple(f"{i:04d}" for i in range(1, count + 1))
    if any(seq not in thermal or seq not in rgb for seq in sequences):
        raise ValueError("selected sequence lacks a thermal or RGB image")
    return MatchedM3TSelection(
        sequences,
        tuple(thermal[seq] for seq in sequences),
        tuple(rgb[seq] for seq in sequences),
    )
