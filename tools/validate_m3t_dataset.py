"""Validate a directory of real DJI M3T thermal originals.

Usage: PYTHONPATH=src python tools/validate_m3t_dataset.py /path/to/flight
No source imagery is modified or copied.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from statistics import fmean

from mcm_solarcheck.importers.m3t_xmp import parse_m3t_xmp
from mcm_solarcheck.thermal.m3t_radiometric import M3TRadiometricParser


def validate(directory: Path) -> int:
    parser = M3TRadiometricParser()
    files = tuple(sorted(directory.glob("*_T.JPG")))
    if not files:
        print("FAIL: no *_T.JPG files found")
        return 2

    failures: list[tuple[str, str]] = []
    minima: list[int] = []
    maxima: list[int] = []
    means: list[float] = []
    rtk_count = 0
    for path in files:
        try:
            data = path.read_bytes()
            raster = parser.parse_bytes(data)
            xmp = parse_m3t_xmp(data)
            minima.append(min(raster.samples)); maxima.append(max(raster.samples)); means.append(fmean(raster.samples))
            if xmp.rtk.status == "RTK": rtk_count += 1
        except Exception as exc:
            failures.append((path.name, f"{type(exc).__name__}: {exc}"))

    print(f"files={len(files)} valid={len(files)-len(failures)} failed={len(failures)} rtk={rtk_count}")
    if minima:
        print(f"raw_min={min(minima)} raw_max={max(maxima)} frame_mean_min={min(means):.6f} frame_mean_max={max(means):.6f}")
    for name, message in failures:
        print(f"FAIL {name}: {message}")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("directory", type=Path)
    return validate(ap.parse_args().directory)


if __name__ == "__main__":
    raise SystemExit(main())
