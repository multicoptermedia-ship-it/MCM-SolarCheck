"""One-command offline two-frame RGB project preview.

Run from a checkout containing this module:
  python -m mcm_solarcheck.services.rgb_project_preview_cli \
    --database TEST_SQLITE --project-id PROJECT_ID \
    --first 0136 --second 0137 --output-dir EXISTING_EMPTY_DIRECTORY

Only a bounded, UNVERIFIED nonmetric PNG and JSON diagnostic are written.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcm_solarcheck.services.rgb_project_preview_vertical import create_project_rgb_preview


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--first", required=True, help="four-digit DJI RGB sequence")
    parser.add_argument("--second", required=True, help="next consecutive RGB sequence")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="already existing EMPTY local output folder")
    arguments = parser.parse_args(argv)
    try:
        result = create_project_rgb_preview(
            arguments.database, arguments.project_id, arguments.first,
            arguments.second, arguments.output_dir,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"RGB preview not generated: {exc}\n")
    print(json.dumps({
        "status": result.status,
        "primary_rgb_frames": [result.first_sequence, result.second_sequence],
        "inliers": result.inliers,
        "canvas_covered_fraction": result.canvas_covered_fraction,
        "median_reprojection_error_px": result.median_reprojection_error_px,
        "image": str(result.png_path),
        "manifest": str(result.manifest_path),
        "metric_orthophoto_verified": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
