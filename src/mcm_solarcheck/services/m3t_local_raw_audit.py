"""Local radiometric format audit for selected M3T ZIP members.

Does not emit raw samples, metadata, coordinates or image data.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from mcm_solarcheck.importers.m3t_pair_selection import select_m3t_pairs
from mcm_solarcheck.thermal.m3t_radiometric import M3TRadiometricParser


@dataclass(frozen=True)
class M3TRawAudit:
    selected_pairs: int
    radiometric_pass: int
    radiometric_fail: int
    sample_count: int
    failed_sequences: tuple[str, ...]


def audit_m3t_raw_archive(
    thermal_zip: str | Path, rgb_zip: str | Path, *, count: int = 29
) -> M3TRawAudit:
    selection = select_m3t_pairs(thermal_zip, rgb_zip, count=count)
    parser = M3TRadiometricParser()
    passed = 0
    samples = 0
    failed: list[str] = []
    with ZipFile(thermal_zip) as archive:
        for seq, name in zip(selection.sequences, selection.thermal_names):
            try:
                raster = parser.parse_bytes(archive.read(name))
                if raster.width != 640 or raster.height != 512:
                    raise ValueError("unexpected raster dimensions")
                passed += 1
                samples += raster.pixel_count
            except (ValueError, OSError) as exc:
                failed.append(seq)
    return M3TRawAudit(len(selection.sequences), passed, len(failed), samples, tuple(failed))
