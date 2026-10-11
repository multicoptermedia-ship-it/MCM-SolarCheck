"""Local-only DJI M3T import smoke test; prints counts, not GPS or image data."""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from mcm_solarcheck.importers.m3t_pair_staging import stage_m3t_pairs
from mcm_solarcheck.importers.project import import_m3t_project


def run(thermal_zip: str | Path, rgb_zip: str | Path) -> dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="mcm-m3t-local-") as directory:
        selection = stage_m3t_pairs(thermal_zip, rgb_zip, directory)
        imported = import_m3t_project(directory)
        return {
            "selected_pairs": len(selection.sequences),
            "rgb_imported": len(imported.rgb_frames),
            "thermal_imported": imported.thermal_batch.summary.imported,
            "thermal_failed": imported.thermal_batch.summary.failed,
            "paired": len(imported.pairs),
            "unpaired_rgb": imported.unpaired_rgb_count,
            "unpaired_thermal": imported.unpaired_thermal_count,
            "raw_candidate_findings": imported.thermal_batch.summary.finding_count,
            "quality_pass": imported.thermal_batch.summary.pass_count,
            "quality_review": imported.thermal_batch.summary.review_count,
            "quality_reject": imported.thermal_batch.summary.reject_count,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate 29 local DJI M3T image pairs")
    parser.add_argument("thermal_zip", type=Path)
    parser.add_argument("rgb_zip", type=Path)
    args = parser.parse_args()
    result = run(args.thermal_zip, args.rgb_zip)
    for key, value in result.items():
        print(f"{key}: {value}")
    if (result["thermal_failed"] or result["paired"] != 29
            or result["rgb_imported"] != 29 or result["thermal_imported"] != 29
            or result["unpaired_rgb"] or result["unpaired_thermal"]):
        raise SystemExit("M3T importer needs review; no report authorized")


if __name__ == "__main__":
    main()
