"""One local project RGB camera-network run; outputs NO claimed metric poses."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from mcm_solarcheck.services.rgb_project_global_camera_network import (
    reconstruct_project_rgb_camera_network,
)


def main(argv=None):
    parser=argparse.ArgumentParser(description="Whole-project UNVERIFIED SfM camera network")
    parser.add_argument("--database",required=True)
    parser.add_argument("--project-id",required=True)
    parser.add_argument("--calibration-json",required=True)
    parser.add_argument("--output-directory",required=True)
    options=parser.parse_args(argv)
    path=Path(options.calibration_json)
    if not path.is_file() or path.is_symlink() or path.stat().st_size>1_000_000:
        raise ValueError("bounded external RGB camera calibration JSON required")
    destination=Path(options.output_directory)
    if not destination.is_dir() or destination.is_symlink() or any(destination.iterdir()):
        raise ValueError("new diagnostic file requires an existing empty output directory")
    evidence=json.loads(path.read_text(encoding="utf-8"))
    result=reconstruct_project_rgb_camera_network(
        options.database,options.project_id,evidence,
    )
    # Relative unscaled poses are deliberately not serialized as a
    # "verified" survey geometry package to the roof tile service.
    summary={
        "schema":"mcm.rgb_global_camera_network.v1",
        "state":result.state,
        "all_imported_rgb_frames_reconstructed":True,
        "camera_count":len(result.frame_ids),
        "linked_image_pairs":result.linked_image_pairs,
        "multi_image_tracks":result.multiview_tracks,
        "reconstructed_landmarks":result.reconstructed_landmarks,
        "reprojection_p95_px":result.reprojection_p95_px,
        "reprojection_max_px":result.reprojection_max_px,
        "metric_scale_verified":False,
        "roof_geometry_verified":False,
        "bundle_adjustment_completed":False,
        "orthophoto_verified":False,
        "thermal_registration_verified":False,
    }
    target=destination/"rgb-global-camera-network-unscaled.json"
    with target.open("x",encoding="utf-8") as stream:
        json.dump(summary,stream,indent=2,sort_keys=True)
        stream.write("\n")
    print(json.dumps({"state":result.state,"frames":len(result.frame_ids),
                      "orthophoto_verified":False},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
