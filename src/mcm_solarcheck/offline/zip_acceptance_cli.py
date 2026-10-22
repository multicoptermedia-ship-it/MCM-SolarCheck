"""Opt-in read-only Windows 10 DJI ZIP acceptance: before and after GUI import.

Does not import, modify projects, initialize databases, publish or train.
Report contains aggregate counters only, never original paths or EXIF values.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from zipfile import BadZipFile

from mcm_solarcheck.importers.m3t_original_archive_audit import audit_original_m3t_archives
from mcm_solarcheck.offline.zip_acceptance import verify_imported_originals


def evaluate(
    thermal_zip: Path,
    rgb_zip: Path,
    *,
    expected_thermal: int = 160,
    expected_rgb: int = 33,
    expected_metadata_pairs: int = 33,
    database: Path | None = None,
    project_id: str | None = None,
    include_unpaired_thermal: bool = False,
) -> dict:
    """Apply an explicit, dataset-specific read-only technical acceptance."""
    if (database is None) != (project_id is None):
        raise ValueError("database and project identifier must be supplied together")
    if not all(type(n) is int and n >= 0 for n in (
        expected_thermal, expected_rgb, expected_metadata_pairs
    )):
        raise ValueError("expected archive counts must be non-negative integers")
    if expected_metadata_pairs > min(expected_rgb, expected_thermal):
        raise ValueError("invalid expected archive pair count")
    audit = audit_original_m3t_archives(thermal_zip, rgb_zip)
    report = audit.summary()
    if (report["thermal_images"] != expected_thermal
            or report["rgb_images"] != expected_rgb
            or report["confirmed_pairs"] != expected_metadata_pairs
            or report["rgb_without_thermal"] != 0
            or report["sequence_timestamp_conflicts"] != 0):
        raise ValueError("real ZIP inventory does not match explicit expectations")
    result = {
        "stage": "pre_import_archive_audit",
        "thermal_images_in_zip": expected_thermal,
        "rgb_images_in_zip": expected_rgb,
        "filename_timestamp_matched_pairs": expected_metadata_pairs,
        "thermal_without_rgb": report["thermal_without_rgb"],
        "archive_integrity_checked": True,
        "radiometric_celsius_validated": False,
    }
    if database is not None:
        result.update(verify_imported_originals(
            database, project_id, audit, thermal_zip, rgb_zip,
            include_unpaired_thermal=include_unpaired_thermal,
        ))
        result["stage"] = "post_import_read_only_verification"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Private read-only acceptance: M3T ZIP counts and optional project originals"
    )
    parser.add_argument("--thermal-zip", type=Path, required=True)
    parser.add_argument("--rgb-zip", type=Path, required=True)
    parser.add_argument("--expected-thermal", type=int, default=160)
    parser.add_argument("--expected-rgb", type=int, default=33)
    parser.add_argument("--expected-metadata-pairs", type=int, default=33)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--project-id")
    parser.add_argument("--include-unpaired-thermal", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = evaluate(
            args.thermal_zip, args.rgb_zip,
            expected_thermal=args.expected_thermal,
            expected_rgb=args.expected_rgb,
            expected_metadata_pairs=args.expected_metadata_pairs,
            database=args.database, project_id=args.project_id,
            include_unpaired_thermal=args.include_unpaired_thermal,
        )
    except (OSError, ValueError, KeyError, PermissionError, BadZipFile,
            sqlite3.DatabaseError, TypeError) as exc:
        # Intentionally never print exception messages: source paths,
        # project identifiers and EXIF metadata are all private.
        print(json.dumps({
            "accepted": False, "failure_type": type(exc).__name__,
            "private_details_not_logged": True,
        }, sort_keys=True))
        return 2
    print(json.dumps({"accepted": True, **result}, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
