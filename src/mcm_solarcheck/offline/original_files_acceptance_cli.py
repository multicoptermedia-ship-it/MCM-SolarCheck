"""Private read-only pre/post GUI acceptance for loose DJI M3T originals."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

from mcm_solarcheck.importers.m3t_original_files_audit import audit_original_m3t_files
from mcm_solarcheck.offline.original_files_acceptance import verify_original_file_project


def select_original_files(source_folders, original_files) -> tuple[Path, ...]:
    """Only explicit JPG selections from specified top-level local directories."""
    selected = [Path(path) for path in original_files]
    for directory in source_folders:
        folder = Path(directory)
        if (not folder.is_absolute() or folder.is_symlink() or not folder.is_dir()):
            raise PermissionError("Explicit existing regular source directory required")
        selected.extend(sorted(
            (path for path in folder.iterdir() if path.suffix.lower() == ".jpg"),
            key=lambda path: path.name.casefold(),
        ))
    return tuple(selected)


def evaluate(
    originals,
    *,
    expected_thermal: int = 160,
    expected_rgb: int = 33,
    expected_metadata_pairs: int = 33,
    database: Path | None = None,
    project_id: str | None = None,
) -> dict:
    if (database is None) != (project_id is None):
        raise ValueError("Provide project ID and database together")
    if (any(type(x) is not int or x < 0 for x in
            (expected_thermal, expected_rgb, expected_metadata_pairs))
            or expected_metadata_pairs > min(expected_thermal, expected_rgb)):
        raise ValueError("Invalid expected counts")
    audit = audit_original_m3t_files(tuple(originals))
    overview = audit.aggregate()
    if (overview["thermal_images"] != expected_thermal
            or overview["rgb_images"] != expected_rgb
            or overview["filename_timestamp_matched_pairs"] != expected_metadata_pairs
            or overview["rgb_without_thermal"] != 0):
        raise ValueError("Selected originals do not match expected pilot set")
    response = {
        "stage": "pre_import_original_file_audit",
        **overview,
        "local_originals_inspected": len(audit.files),
    }
    if database is not None:
        response.update(verify_original_file_project(database, project_id, audit))
        response["stage"] = "post_import_read_only_verification"
    return response


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only loose DJI image acceptance")
    parser.add_argument("--source-folder", type=Path, action="append", default=[])
    parser.add_argument("--original-file", type=Path, action="append", default=[])
    parser.add_argument("--expected-thermal", type=int, default=160)
    parser.add_argument("--expected-rgb", type=int, default=33)
    parser.add_argument("--expected-metadata-pairs", type=int, default=33)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--project-id")
    args = parser.parse_args(argv)
    try:
        originals = select_original_files(args.source_folder, args.original_file)
        report = evaluate(
            originals,
            expected_thermal=args.expected_thermal,
            expected_rgb=args.expected_rgb,
            expected_metadata_pairs=args.expected_metadata_pairs,
            database=args.database,
            project_id=args.project_id,
        )
    except (OSError, ValueError, KeyError, TypeError, PermissionError,
            sqlite3.DatabaseError) as exc:
        # Explicitly do not leak filenames, absolute private paths, EXIF, GPS,
        # original pixel content or full exception text in logs.
        print(json.dumps({
            "accepted": False, "failure_type": type(exc).__name__,
            "private_details_not_logged": True,
        }, sort_keys=True))
        return 2
    print(json.dumps({"accepted": True, **report}, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
