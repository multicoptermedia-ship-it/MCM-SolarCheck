"""Explicit, atomic-styled local staging of verified real M3T thermal/RGB ZIPs.

Existing project data, original ZIPs, admin accounts and AI training ledgers
are never touched. This operation is NOT an expert defect or Celsius approval.
Only a NEW, caller-specified directory can be created. Keep all files private.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from zipfile import ZipFile

from mcm_solarcheck.importers.m3t_original_archive_audit import (
    audit_original_m3t_archives,
)

MAX_TOTAL_STAGED_BYTES = 6_000_000_000


def stage_original_m3t_archives(
    thermal_zip: str | Path, rgb_zip: str | Path, destination: str | Path, *,
    include_unpaired_thermal: bool = False,
) -> dict:
    """Copy intact sources with checksums, without editing/decoding the images.

    Do not quietly stage an RGB counterpart whose timestamp conflicts with
    its thermal partner. The staged flat folder can later be passed to the
    existing M3T import engine after an explicit project-local selection.
    """
    if type(include_unpaired_thermal) is not bool:
        raise TypeError("explicit Boolean for unpaired thermal staging required")
    target = Path(destination)
    if (not target.is_absolute() or target.exists() or target.is_symlink()
            or not target.parent.is_dir() or target.parent.is_symlink()):
        raise PermissionError("new absolute destination in real existing parent required")
    selection = audit_original_m3t_archives(thermal_zip, rgb_zip)
    if selection.mismatched_timestamp_sequences or selection.rgb_only_sequences:
        raise PermissionError("ambiguous, mismatched or unmatched RGB frames cannot be staged")
    if not selection.paired_sequences:
        raise ValueError("at least one exact thermal/RGB pair required")
    included = set(selection.paired_sequences)
    if include_unpaired_thermal:
        included.update(selection.thermal_only_sequences)
    ordered_t = [x for x in selection.thermal if x.sequence in included]
    ordered_v = [x for x in selection.rgb if x.sequence in included]
    amount = sum(x.size_bytes for x in (*ordered_t, *ordered_v))
    if amount > MAX_TOTAL_STAGED_BYTES:
        raise ValueError("staging exceeds local resource budget")
    manifest = {
        "schema": 1,
        "status": "private_originals_not_report_or_training_approved",
        "camera": "DJI M3T",
        "capture_formats": "original DJI JPEG/MPO; no radiometric Celsius claim",
        "matched_pairs": len(selection.paired_sequences),
        "staged_thermal": len(ordered_t),
        "staged_rgb": len(ordered_v),
        "unpaired_thermal_not_staged": len(selection.thermal_only_sequences)
            if not include_unpaired_thermal else 0,
        "unpaired_thermal_explicitly_staged": len(selection.thermal_only_sequences)
            if include_unpaired_thermal else 0,
        "files": [],
    }
    target.mkdir(mode=0o700)
    try:
        for archive_path, entries in ((thermal_zip, ordered_t), (rgb_zip, ordered_v)):
            with ZipFile(archive_path) as archive:
                for item in entries:
                    info = archive.getinfo(item.name)
                    if info.file_size != item.size_bytes:
                        raise ValueError("source archive changed during staging")
                    result = target / item.name
                    digest = sha256()
                    total = 0
                    with archive.open(info) as incoming, result.open("xb") as outgoing:
                        while chunk := incoming.read(1024 * 1024):
                            total += len(chunk)
                            if total > item.size_bytes:
                                raise ValueError("source bytes grew during copy")
                            digest.update(chunk)
                            outgoing.write(chunk)
                        outgoing.flush()
                        os.fsync(outgoing.fileno())
                    if total != item.size_bytes:
                        raise ValueError("truncated source image")
                    manifest["files"].append({
                        "filename": item.name,
                        "sequence": item.sequence,
                        "modality": item.modality,
                        "bytes": total,
                        "sha256": digest.hexdigest(),
                        "human_reviewed": False,
                        "training_rights_approved": False,
                    })
        with (target / "m3t-original-provenance.json").open(
            "x", encoding="utf-8",
        ) as output:
            json.dump(manifest, output, sort_keys=True, indent=2)
            output.write("\n")
        return {
            "matched_pairs": manifest["matched_pairs"],
            "staged_thermal": manifest["staged_thermal"],
            "staged_rgb": manifest["staged_rgb"],
            "unpaired_thermal_not_staged": manifest["unpaired_thermal_not_staged"],
            "unpaired_thermal_explicitly_staged":
                manifest["unpaired_thermal_explicitly_staged"],
            "status": manifest["status"],
        }
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise
