"""Local-only command-line DJI archive pairing check.

Usage: python -m mcm_solarcheck.services.flight_zip_check /path/to/flight.zip
No original images, GPS positions or filenames are sent to a remote service.
"""
from __future__ import annotations

import argparse

from mcm_solarcheck.services.flight_zip_preflight import inspect_dji_flight_zip


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline DJI RGB/thermal flight ZIP preflight")
    parser.add_argument("archive", help="local DJI inspection ZIP")
    args = parser.parse_args(argv)
    try:
        result = inspect_dji_flight_zip(args.archive)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Flight ZIP preflight failed: {error}\n")
    print(f"RGB: {result.rgb_count}; thermal: {result.thermal_count}; timestamp-matched pairs: {result.paired_count}")
    print(f"Unpaired IDs: {len(result.unpaired_ids)}; timestamp mismatches: {len(result.mismatched_timestamps)}")
    for note in result.diagnostics:
        print(f"NOTE: {note}")
    return 0 if result.paired_count and not result.unpaired_ids and not result.mismatched_timestamps else 1


if __name__ == "__main__":
    raise SystemExit(main())
