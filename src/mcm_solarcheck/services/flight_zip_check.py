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
    parser.add_argument("--audit-geometry", action="store_true", help="inspect DJI XMP references locally; never approve geometry")
    parser.add_argument("--inspect-images", action="store_true", help="read JPEG headers locally; no geometry approval")
    args = parser.parse_args(argv)
    try:
        result = inspect_dji_flight_zip(args.archive)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Flight ZIP preflight failed: {error}\n")
    print(f"RGB: {result.rgb_count}; thermal: {result.thermal_count}; timestamp-matched pairs: {result.paired_count}")
    print(f"Unpaired IDs: {len(result.unpaired_ids)}; timestamp mismatches: {len(result.mismatched_timestamps)}")
    for note in result.diagnostics:
        print(f"NOTE: {note}")
    if args.inspect_images:
        from mcm_solarcheck.services.flight_image_readiness import inspect_flight_image_readiness
        try:
            images = inspect_flight_image_readiness(args.archive)
        except (ValueError, OSError) as error:
            parser.exit(2, f"JPEG inspection failed: {error}\\n")
        print(f"Decoded RGB JPEGs: {images.rgb_images}; thermal JPEGs: {images.thermal_images}; multichannel thermal: {images.thermal_palette_images}")
        print(f"RGB dimensions: {images.rgb_dimensions}; thermal dimensions: {images.thermal_dimensions}")
        for note in images.diagnostics:
            print(f"NOTE: {note}")
    if args.audit_geometry:
        from mcm_solarcheck.services.flight_geometry_audit import audit_dji_flight_geometry
        try:
            audit = audit_dji_flight_geometry(args.archive)
        except (ValueError, OSError) as error:
            parser.exit(2, f"XMP geometry audit failed: {error}\\n")
        print(f"XMP RGB: {audit.rgb_count}; thermal: {audit.thermal_count}; missing poses: {audit.missing_pose_count}")
        print(f"RGB sources: {audit.rgb_sources}; thermal sources: {audit.thermal_sources}")
        print(f"RGB GPS statuses: {audit.rgb_gps_statuses}; thermal GPS statuses: {audit.thermal_gps_statuses}")
        for note in audit.diagnostics:
            print(f"NOTE: {note}")
    return 0 if result.paired_count and not result.unpaired_ids and not result.mismatched_timestamps else 1


if __name__ == "__main__":
    raise SystemExit(main())
