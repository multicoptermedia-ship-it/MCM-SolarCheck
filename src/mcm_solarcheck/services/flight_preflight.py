"""Streaming, read-only preflight for large DJI Mavic 3T source folders.

This inventory matches the current top-level *_V.JPG / *_T.JPG import
contract. It examines directory entries and file sizes only; it does not
decode images, verify RGB/thermal pairing, calibrate temperatures, write
files, or claim georeferencing.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Callable


class FlightPreflightCancelled(Exception):
    """Cooperative cancellation before a complete inventory was produced."""


@dataclass(frozen=True)
class FlightPreflightResult:
    source_folder: Path
    entries_seen: int
    rgb_files: int
    thermal_files: int
    rgb_bytes: int
    thermal_bytes: int
    empty_images: int
    symlinks: int
    other_entries: int
    inaccessible_entries: int
    issue_examples: tuple[str, ...]
    read_only: bool = True
    image_pixels_decoded: bool = False
    pairing_verified: bool = False


def scan_dji_flight_preflight(
    folder: str | Path,
    *,
    on_progress: Callable[[int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    progress_interval: int = 100,
    max_issue_examples: int = 8,
) -> FlightPreflightResult:
    """Scan a folder in one pass without retaining an unbounded file list.

    Statistics describe what was observed at scan time, not an atomic
    filesystem snapshot. Only regular, non-link *_V.JPG and *_T.JPG files in
    the selected directory count toward importer-compatible image totals.
    """
    if type(progress_interval) is not int or progress_interval < 1:
        raise ValueError("progress_interval must be a positive integer")
    if type(max_issue_examples) is not int or not (0 <= max_issue_examples <= 32):
        raise ValueError("max_issue_examples must be between 0 and 32")
    source = Path(folder)
    if source.is_symlink() or not source.is_dir():
        raise ValueError("existing, non-symlink local DJI folder required")

    entries = rgb = thermal = rgb_bytes = thermal_bytes = 0
    empty = links = other = inaccessible = 0
    examples: list[str] = []

    def cancelled() -> None:
        if should_cancel is not None and should_cancel():
            raise FlightPreflightCancelled("DJI folder preflight cancelled")

    def issue(text: str) -> None:
        if len(examples) < max_issue_examples:
            examples.append(text)

    cancelled()
    with os.scandir(source) as directory:
        for entry in directory:
            cancelled()
            entries += 1
            if entry.is_symlink():
                links += 1
                issue(f"Symbolischer Link ignoriert: {entry.name}")
            else:
                try:
                    regular = entry.is_file(follow_symlinks=False)
                except OSError:
                    inaccessible += 1
                    issue(f"Eintrag nicht lesbar: {entry.name}")
                    regular = None
                if regular is False:
                    other += 1
                elif regular:
                    if entry.name.endswith("_V.JPG"):
                        modality = "rgb"
                    elif entry.name.endswith("_T.JPG"):
                        modality = "thermal"
                    else:
                        modality = None
                        other += 1
                        if entry.name.upper().endswith(("_V.JPG", "_T.JPG")):
                            issue(f"Namensschreibweise vom Import nicht erfasst: {entry.name}")
                    if modality is not None:
                        try:
                            size = entry.stat(follow_symlinks=False).st_size
                        except OSError:
                            inaccessible += 1
                            issue(f"Bildgröße nicht lesbar: {entry.name}")
                        else:
                            if modality == "rgb":
                                rgb += 1
                                rgb_bytes += size
                            else:
                                thermal += 1
                                thermal_bytes += size
                            if size == 0:
                                empty += 1
                                issue(f"Leere Bilddatei: {entry.name}")
            if on_progress is not None and entries % progress_interval == 0:
                on_progress(entries)
    cancelled()
    if on_progress is not None:
        on_progress(entries)
    return FlightPreflightResult(
        source_folder=source,
        entries_seen=entries,
        rgb_files=rgb,
        thermal_files=thermal,
        rgb_bytes=rgb_bytes,
        thermal_bytes=thermal_bytes,
        empty_images=empty,
        symlinks=links,
        other_entries=other,
        inaccessible_entries=inaccessible,
        issue_examples=tuple(examples),
    )
