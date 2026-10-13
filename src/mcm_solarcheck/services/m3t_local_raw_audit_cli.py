"""CLI for privacy-safe DJI M3T radiometric ZIP audit."""
from __future__ import annotations

import argparse
from pathlib import Path

from mcm_solarcheck.services.m3t_local_raw_audit import audit_m3t_raw_archive


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit selected DJI M3T thermal raw streams locally")
    parser.add_argument("thermal_zip", type=Path)
    parser.add_argument("rgb_zip", type=Path)
    parser.add_argument("--count", type=int, default=29)
    args = parser.parse_args()
    result = audit_m3t_raw_archive(args.thermal_zip, args.rgb_zip, count=args.count)
    print(f"selected_pairs: {result.selected_pairs}")
    print(f"radiometric_pass: {result.radiometric_pass}")
    print(f"radiometric_fail: {result.radiometric_fail}")
    print(f"sample_count: {result.sample_count}")
    if result.failed_sequences:
        print("failed_sequences: " + ", ".join(result.failed_sequences))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
