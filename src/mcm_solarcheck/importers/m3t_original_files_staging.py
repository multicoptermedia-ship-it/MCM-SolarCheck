"""Private, lossless staging of *selected unpacked* DJI M3T original files.

This is the primary desktop input. ZIP is optional transport-only; neither
training rights nor temperature accuracy nor sensor registration are granted.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import shutil

from mcm_solarcheck.importers.m3t_original_files_audit import audit_original_m3t_files


def stage_original_m3t_files(original_files, destination, *,
                             should_cancel=None, on_file_copied=None) -> dict:
    """Verify and permanently copy only manually selected original images.

    Filenames, EXIF metadata, source paths and GPS never leave the private
    local manifest. All files are validated before any staging directory
    is created, and new copies are deleted if any later step fails.
    """
    target = Path(destination)
    if (not target.is_absolute() or target.exists() or target.is_symlink()
            or not target.parent.is_dir() or target.parent.is_symlink()):
        raise PermissionError("A new private destination in an existing directory is required")
    audit = audit_original_m3t_files(original_files, should_cancel=should_cancel)
    checked = [
        (item.path, item.modality, item.sequence, item.exposure, item.size_bytes)
        for item in audit.files
    ]
    matched, count_t, count_v, unpaired_t = (
        audit.matched_pairs, audit.thermal_images, audit.rgb_images,
        audit.thermal_only,
    )
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
