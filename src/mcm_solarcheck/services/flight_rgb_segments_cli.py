"""Offline CLI for exporting all bounded RGB segment previews from a DJI folder.

Usage: python -m mcm_solarcheck.services.flight_rgb_segments_cli FOLDER REGISTRATION_JSON OUTPUT_DIR
"""
import argparse
import json
from pathlib import Path

from mcm_solarcheck.services.flight_rgb_all_segments import save_all_flight_rgb_segments


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="DJI flight image folder")
    parser.add_argument("registration_json", type=Path, help="saved RGB link registration JSON")
    parser.add_argument("output_dir", type=Path, help="existing empty output directory")
    args = parser.parse_args(argv)
    try:
        with args.registration_json.open(encoding="utf-8") as stream:
            registration = json.load(stream)
        result = save_all_flight_rgb_segments(
            args.folder, registration, args.output_dir,
            on_progress=lambda done, total, record: print(
                f"{done}/{total}: segment {record['index']} {record['status']}", flush=True
            ),
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"RGB segment export failed: {exc}\n")
    print(json.dumps({key: result[key] for key in
                      ("segment_count", "exported", "failed", "cancelled")}))
    return 1 if result["failed"] or result["cancelled"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
