"""Local read-only six-archive RGB flight run; never export private coordinates.

Example (user-local paths):
python -m mcm_solarcheck.services.rgb_zip_whole_flight_cli \\
  --rgb-archive RGB7.zip --rgb-archive RGB6.zip ... \\
  --calibration-json independent-camera.json --report absolute-local-report.json

The JPEG originals are opened from ZIP members in memory, never extracted.
Only aggregated diagnostic numbers go to JSON/stdout; no 3D roof output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcm_solarcheck.services.rgb_zip_whole_flight_reconstruction import (
    PrivateRGBFlightStageError, reconstruct_private_complete_rgb_zip_flight,
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="PRIVATE whole-flight RGB SfM + RTK windowed BA (not an orthophoto)",
    )
    parser.add_argument("--rgb-archive", action="append", required=True,
                        help="local RGB ZIP/.tip path; repeat for all flight archives")
    parser.add_argument("--calibration-json", type=Path, required=True,
                        help="independently verified RGB lens calibration JSON")
    parser.add_argument("--report", type=Path,
                        help="optional NEW absolute local JSON (no GPS/images)")
    parser.add_argument("--max-side", type=int, default=1200)
    parser.add_argument("--max-features", type=int, default=1600)
    parser.add_argument("--expected-frames", type=int, default=160,
                        help="required complete RGB frame count; Hummintech default 160")
    parser.add_argument("--expected-archives", type=int, default=6,
                        help="required private RGB ZIP/.tip count; Hummintech default 6")
    parser.add_argument("--first-counter", type=int, default=1,
                        help="first exact DJI V-JPEG four-digit counter; default 0001")
    args = parser.parse_args(argv)
    archives = tuple(Path(value) for value in args.rgb_archive)
    calibration_file = args.calibration_json
    if (not calibration_file.is_file() or calibration_file.is_symlink()
            or calibration_file.stat().st_size > 1_000_000):
        raise ValueError("existing bounded external calibration file required")
    report_file = args.report
    if report_file is not None:
        if (not report_file.is_absolute() or report_file.is_symlink()
                or report_file.exists() or not report_file.parent.is_dir()
                or report_file.parent.is_symlink()
                or report_file.parent.resolve() in {
                    path.resolve().parent for path in archives
                }):
            raise ValueError("new local report outside every RGB archive folder required")
    try:
        calibration = json.loads(calibration_file.read_text(encoding="utf-8"))
        outcome = reconstruct_private_complete_rgb_zip_flight(
            archives, calibration,
            max_side=args.max_side, max_features=args.max_features,
            expected_frame_count=args.expected_frames,
            expected_archive_count=args.expected_archives,
            first_counter=args.first_counter,
        )
        result = outcome.privacy_safe_summary()
        status = 0
    except PrivateRGBFlightStageError as failed:
        result = {
            "schema": "mcm.private_complete_rgb_flight_reconstruction.v1",
            "status": "whole_flight_rgb_quality_gate_failed",
            "failed_stage": failed.stage,
            "all_input_rgb_frames_processed": False,
            "roof_geometry_verified": False,
            "rgb_orthophoto_verified": False,
            "module_analysis_verified": False,
            "thermal_registration_verified": False,
        }
        status = 2
    except (ValueError, TypeError, json.JSONDecodeError):
        result = {
            "schema": "mcm.private_complete_rgb_flight_reconstruction.v1",
            "status": "whole_flight_rgb_calibration_gate_failed",
            "failed_stage": "calibration",
            "all_input_rgb_frames_processed": False,
            "roof_geometry_verified": False,
            "rgb_orthophoto_verified": False,
            "module_analysis_verified": False,
            "thermal_registration_verified": False,
        }
        status = 2
    if report_file is not None:
        with report_file.open("x", encoding="utf-8") as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write("\n")
    print(json.dumps(result, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
