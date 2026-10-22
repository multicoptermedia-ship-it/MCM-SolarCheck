"""Private, lossless staging of *selected unpacked* DJI M3T original files.

This is the primary desktop input. ZIP is optional transport-only; neither
training rights nor temperature accuracy nor sensor registration are granted.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from PIL import Image
import json
import os
import re
import shutil

from mcm_solarcheck.importers.m3t_original_zip_staging import MAX_TOTAL_STAGED_BYTES

DJI_ORIGINAL = re.compile(r"DJI_(\d{14})_(\d{4})_([TV])\.JPG\Z", re.IGNORECASE)
MAX_FILE_BYTES = {"T": 30_000_000, "V": 40_000_000}
MAX_FILES = 15_000


def stage_original_m3t_files(original_files, destination, *,
                             should_cancel=None, on_file_copied=None) -> dict:
    """Verify and permanently copy only manually selected original images.

    Filenames, EXIF metadata, source paths and GPS never leave the private
    local manifest. All files are validated before any staging directory
    is created, and new copies are deleted if any later step fails.
    """
    if not isinstance(original_files, (list, tuple)):
        raise TypeError("A selected sequence of original files is required")
    if not 1 <= len(original_files) <= MAX_FILES:
        raise ValueError("Select at least one and at most 15000 DJI originals")
    target = Path(destination)
    if (not target.is_absolute() or target.exists() or target.is_symlink()
            or not target.parent.is_dir() or target.parent.is_symlink()):
        raise PermissionError("A new private destination in an existing directory is required")
    checked: list[tuple[Path, str, str, str, int]] = []
    used_names: set[str] = set()
    used_counters: set[tuple[str, str]] = set()
    timestamps: dict[str, dict[str, str]] = {}
    total = 0
    for selected in original_files:
        if should_cancel is not None and should_cancel():
            raise InterruptedError("Original image staging cancelled")
        path = Path(selected)
        if (not path.is_absolute() or path.is_symlink() or not path.is_file()
                or path.parent.is_symlink()):
            raise PermissionError("Only selected local regular image files are allowed")
        match = DJI_ORIGINAL.fullmatch(path.name)
        if match is None:
            raise ValueError("Invalid original DJI M3T filename")
        stamp, seq, kind = match.group(1), match.group(2), match.group(3).upper()
        datetime.strptime(stamp, "%Y%m%d%H%M%S")
        if path.name.casefold() in used_names or (kind, seq) in used_counters:
            raise ValueError("Duplicated original DJI image identity")
        used_names.add(path.name.casefold())
        used_counters.add((kind, seq))
        size = path.stat().st_size
        if not 0 < size <= MAX_FILE_BYTES[kind]:
            raise ValueError("Invalid DJI original byte size")
        total += size
        if total > MAX_TOTAL_STAGED_BYTES:
            raise ValueError("Selected original files exceed local resource limit")
        with Image.open(path) as image:
            if image.format not in ("MPO", "JPEG"):
                raise ValueError("Unsupported DJI image container")
            if image.size != ((640, 512) if kind == "T" else (4000, 3000)):
                raise ValueError("Unexpected DJI image dimensions")
            tags = image.getexif()
            expected_time = (
                f"{stamp[:4]}:{stamp[4:6]}:{stamp[6:8]} "
                f"{stamp[8:10]}:{stamp[10:12]}:{stamp[12:14]}"
            )
            if (tags.get(271) != "DJI" or tags.get(272) != "M3T"
                    or tags.get(306) != expected_time):
                raise ValueError("Original DJI EXIF identity or capture time mismatch")
        timestamps.setdefault(seq, {})[kind] = stamp
        checked.append((path, kind, seq, stamp, size))
    if any(len(both) == 2 and both["T"] != both["V"]
           for both in timestamps.values()):
        raise ValueError("RGB/Thermal counters with conflicting exposure timestamps")
    matched = sum(len(both) == 2 for both in timestamps.values())
    count_t = sum(kind == "T" for _, kind, _, _, _ in checked)
    count_v = len(checked) - count_t
    unpaired_t = sum("T" in both and "V" not in both for both in timestamps.values())
    # The operator explicitly selected these individual originals; do not
    # silently exclude thermal-only images or manufacture missing RGB partners.
    manifest = {
        "schema": 1,
        "status": "private_originals_not_report_or_training_approved",
        "camera": "DJI M3T",
        "capture_formats": "original DJI JPEG/MPO; no radiometric Celsius claim",
        "input_mode": "selected_original_files",
        "matched_pairs": matched,
        "staged_thermal": count_t,
        "staged_rgb": count_v,
        "unpaired_thermal_not_staged": 0,
        "unpaired_thermal_explicitly_staged": unpaired_t,
        "files": [],
    }
    target.mkdir(mode=0o700)
    try:
        for source, kind, sequence, _stamp, size in checked:
            if should_cancel is not None and should_cancel():
                raise InterruptedError("Original image staging cancelled")
            digest = sha256()
            written = 0
            output = target / source.name
            with source.open("rb") as incoming, output.open("xb") as outgoing:
                while data := incoming.read(1024 * 1024):
                    if should_cancel is not None and should_cancel():
                        raise InterruptedError("Original image staging cancelled")
                    written += len(data)
                    if written > size:
                        raise ValueError("Original image changed while copying")
                    digest.update(data)
                    outgoing.write(data)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            if written != size:
                raise ValueError("Original image truncated during copying")
            manifest["files"].append({
                "filename": source.name, "sequence": sequence,
                "modality": kind, "bytes": size, "sha256": digest.hexdigest(),
                "human_reviewed": False, "training_rights_approved": False,
            })
            if on_file_copied is not None:
                on_file_copied(len(manifest["files"]))
        if should_cancel is not None and should_cancel():
            raise InterruptedError("Original image staging cancelled")
        with (target / "m3t-original-provenance.json").open(
            "x", encoding="utf-8"
        ) as output:
            json.dump(manifest, output, sort_keys=True, indent=2)
            output.write("\n")
        return {
            "matched_pairs": matched,
            "staged_thermal": count_t,
            "staged_rgb": count_v,
            "explicit_thermal_without_rgb": unpaired_t,
            "status": manifest["status"],
        }
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise
