"""One local project RGB camera-network run; outputs NO claimed metric poses."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np

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
    # Keep the actual multi-view 3D observations as a compact local NPZ bundle
    # so future BA can operate without rebuilding expensive ORB feature tracks.
    # This is deliberately NOT an importable metric roof-geometry package.
    package=destination/"rgb-global-camera-network-unscaled.npz"
    target=destination/"rgb-global-camera-network-unscaled.json"
    written=[]
    try:
        with package.open("xb") as stream:
            written.append(package)
            np.savez_compressed(
                stream,
                poses_world_to_camera_arbitrary=np.stack(result.world_to_camera),
                landmarks_xyz_arbitrary=result.landmark_xyz_unit_baseline,
                observation_landmark_indices=result.observation_landmark_indices,
                observation_frame_indices=result.observation_frame_indices,
                observation_pixels_xy=result.observation_pixels_xy,
                calibrated_intrinsics=np.array([
                    evidence["intrinsics"][field] for field in ("fx","fy","cx","cy")
                ],dtype=np.float64),
            )
        summary["unscaled_track_bundle"]="rgb-global-camera-network-unscaled.npz"
        summary["unscaled_3d_coordinates_not_metric"]=True
        summary["camera_frame_ids"]=list(result.frame_ids)
        with target.open("x",encoding="utf-8") as stream:
            written.append(target)
            json.dump(summary,stream,indent=2,sort_keys=True)
            stream.write("\n")
    except BaseException:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    print(json.dumps({"state":result.state,"frames":len(result.frame_ids),
                      "orthophoto_verified":False},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
