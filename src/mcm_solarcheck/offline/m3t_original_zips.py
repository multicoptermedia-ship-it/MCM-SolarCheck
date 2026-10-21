"""Operator-invoked, entirely offline validation of DJI M3T original ZIPs.

Does not download, upload, change a SolarCheck database, release a report or
authorize model training. Only aggregate counts appear in logs and reports.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from mcm_solarcheck.importers.m3t_original_archive_audit import (
    audit_original_m3t_archives,
)
from mcm_solarcheck.importers.m3t_original_zip_staging import (
    stage_original_m3t_archives,
)
from mcm_solarcheck.thermal.m3t_radiometric import M3TRadiometricParser


def audit_raw_app3(thermal_zip: Path, names: tuple[str, ...]) -> int:
    """Confirm expected APP3 raw raster structure without yielding Celsius."""
    parser = M3TRadiometricParser()
    checked = 0
    with ZipFile(thermal_zip) as archive:
        for name in names:
            with archive.open(name) as source:
                raw = source.read(30_000_001)
            if len(raw) > 30_000_000:
                raise ValueError("thermal member exceeds size cap")
            raster = parser.parse_bytes(raw)
            if (raster.width != 640 or raster.height != 512
                    or raster.pixel_count != 327_680):
                raise ValueError("unexpected raw thermal raster dimensions")
            checked += 1
    return checked


def run_local_archive_audit(
    thermal_zip: Path, rgb_zip: Path, *,
    report_path: Path | None = None,
    staged_directory: Path | None = None,
    include_unpaired_thermal: bool = False,
    verify_raw_app3: bool = False,
) -> dict:
    result = audit_original_m3t_archives(thermal_zip, rgb_zip)
    summary = result.summary()
    if verify_raw_app3:
        summary["raw_raster_app3_structural_validated"] = audit_raw_app3(
            thermal_zip, tuple(x.name for x in result.thermal),
        )
        summary["radiometric_celsius_validated"] = False
    if staged_directory is not None:
        if result.mismatched_timestamp_sequences or result.rgb_only_sequences:
            raise PermissionError("unsafe pair identity; no staging allowed")
        summary["local_staging"] = stage_original_m3t_archives(
            thermal_zip, rgb_zip, staged_directory,
            include_unpaired_thermal=include_unpaired_thermal,
        )
    if report_path is not None:
        if (not report_path.is_absolute() or report_path.is_symlink()
                or not report_path.parent.is_dir() or report_path.parent.is_symlink()):
            raise PermissionError("existing report folder and absolute report path required")
        with report_path.open("x", encoding="utf-8") as output:
            json.dump(summary, output, sort_keys=True, indent=2)
            output.write("\n")
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Private local DJI M3T original ZIP inspection and pair staging",
    )
    parser.add_argument("--thermal-zip", type=Path, required=True)
    parser.add_argument("--rgb-zip", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--stage-new-folder", type=Path)
    parser.add_argument("--include-unpaired-thermal", action="store_true")
    parser.add_argument("--verify-raw-app3", action="store_true")
    args = parser.parse_args(argv)
    if args.include_unpaired_thermal and args.stage_new_folder is None:
        parser.error("unpaired thermal staging requires --stage-new-folder")
    try:
        summary = run_local_archive_audit(
            args.thermal_zip, args.rgb_zip,
            report_path=args.report,
            staged_directory=args.stage_new_folder,
            include_unpaired_thermal=args.include_unpaired_thermal,
            verify_raw_app3=args.verify_raw_app3,
        )
    except (OSError, ValueError, PermissionError, BadZipFile) as exc:
        parser.exit(2, f"Private M3T ZIP audit failed: {type(exc).__name__}\n")
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
