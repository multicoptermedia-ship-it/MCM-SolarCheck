"""Run the production cadence detector on named local M3T control images.

This utility intentionally contains no detector logic. It imports the repository
production detector so a validation result is tied to the checked-out commit.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from mcm_solarcheck.vision.cadence_module_detector import CadenceConfirmedModuleDetector

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path)
    args = parser.parse_args()
    detector = CadenceConfirmedModuleDetector()
    results = []
    for image in args.images:
        detections = detector.detect(image)
        results.append({"image": image.name, "exists": image.is_file(), "detector": detector.name, "module_count": len(detections)})
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
