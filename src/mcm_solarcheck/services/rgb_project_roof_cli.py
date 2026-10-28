"""Offline project-wide RGB roof tile entry point; no ODM/online backend."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from mcm_solarcheck.services.rgb_project_roof_vertical import create_project_rgb_roof_tiles


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Project-wide RGB roof tiles; independent external geometry required",
    )
    parser.add_argument("--database", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--geometry-json", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    path = Path(args.geometry_json)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 4_000_000:
        raise ValueError("regular bounded external geometry JSON required")
    package = json.loads(path.read_text(encoding="utf-8"))
    result = create_project_rgb_roof_tiles(
        args.database, args.project_id, package, args.output_dir,
    )
    print(json.dumps({
        "status": result.status,
        "rgb_frames": result.source_count,
        "tiles": result.tile_count,
        "coverage_fraction": result.coverage_fraction,
        "maximum_held_out_error_m": result.maximum_control_error_m,
        "orthophoto_verified": False,
        "georeferencing_verified": False,
        "control_provenance_authenticated": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
