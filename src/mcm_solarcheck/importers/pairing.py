"""Deterministic RGB/Thermal pairing primitives.

M3T filenames normally expose a shared sequence number (e.g. 0001_V/0001_T).
The pairing engine is intentionally isolated so timestamp/GPS fallback logic can
be added without coupling it to image decoding or the DJI SDK.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

_SEQUENCE_RE = re.compile(r"_(\d{4,})_[VT](?:\.[^.]+)?$", re.IGNORECASE)


def sequence_number(path: Path) -> int | None:
    """Return a DJI sequence number from a V/T filename, if present."""
    match = _SEQUENCE_RE.search(path.name)
    return int(match.group(1)) if match else None


def pair_by_sequence(
    rgb_files: Iterable[Path], thermal_files: Iterable[Path]
) -> list[tuple[Path, Path]]:
    """Pair RGB and thermal files by their shared DJI sequence number."""
    rgb = {sequence_number(p): p for p in rgb_files if sequence_number(p) is not None}
    thermal = {sequence_number(p): p for p in thermal_files if sequence_number(p) is not None}
    return [(rgb[n], thermal[n]) for n in sorted(rgb.keys() & thermal.keys())]
