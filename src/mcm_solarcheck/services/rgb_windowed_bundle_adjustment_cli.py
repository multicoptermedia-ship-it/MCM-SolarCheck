"""Explicitly unscaled whole-project NPZ -> windowed BA, offline and read-only.

Does NOT touch RGB photos or the project SQLite. Emits into a pre-existing
empty output folder; no projected orthophoto/geospatial export is enabled.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

import numpy as np

from mcm_solarcheck.services.rgb_global_camera_network import RGBUnscaledNetwork
from mcm_solarcheck.services.rgb_windowed_bundle_adjustment import (
    adjust_windowed_unscaled_rgb_network,
)
from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics


def main(argv=None):
    parser=argparse.ArgumentParser(description="Windowed RGB BA (UNSCALED, NO orthophoto)")
    parser.add_argument("--source-npz",required=True)
    parser.add_argument("--source-json",required=True)
    parser.add_argument("--output-directory",required=True)
    arguments=parser.parse_args(argv)
    source=Path(arguments.source_npz)
    manifest=Path(arguments.source_json)
    target=Path(arguments.output_directory)
    if (source == manifest or not source.is_file() or source.is_symlink()
            or not manifest.is_file() or manifest.is_symlink()
            or source.stat().st_size>50_000_000 or manifest.stat().st_size>1_000_000
            or not target.is_dir() or target.is_symlink() or any(target.iterdir())):
        raise ValueError("bounded regular unscaled inputs and existing empty output directory required")
    if any(target.resolve() == p.resolve() or target.resolve() in p.resolve().parents
           for p in (source,manifest)):
        raise ValueError("output must not contain unscaled source files")
    summary=json.loads(manifest.read_text(encoding="utf-8"))
    if (not isinstance(summary,dict)
            or summary.get("schema")!="mcm.rgb_global_camera_network.v1"
            or summary.get("unscaled_track_bundle")!=source.name
            or summary.get("metric_scale_verified") is not False
            or summary.get("orthophoto_verified") is not False
            or summary.get("bundle_adjustment_completed") is not False):
        raise ValueError("valid explicitly unscaled RGB SfM manifest required")
    with zipfile.ZipFile(source) as zf:
        if (len(zf.infolist())>12 or any(
                entry.file_size>50_000_000 for entry in zf.infolist())
                or sum(entry.file_size for entry in zf.infolist())>90_000_000):
            raise ValueError("untrusted oversized SfM NPZ archive")
    with np.load(source,allow_pickle=False) as data:
        names={
            "poses_world_to_camera_arbitrary",
            "landmarks_xyz_arbitrary",
            "observation_landmark_indices",
            "observation_frame_indices",
            "observation_pixels_xy",
            "calibrated_intrinsics",
        }
        if set(data.files)!=names:
            raise ValueError("incomplete local unscaled feature track bundle")
        pose=data["poses_world_to_camera_arbitrary"]
        points=data["landmarks_xyz_arbitrary"]
        lid=data["observation_landmark_indices"]
        fid=data["observation_frame_indices"]
        xy=data["observation_pixels_xy"]
        k=data["calibrated_intrinsics"]
    if (k.shape!=(4,) or not np.isfinite(k).all()
            or not isinstance(summary.get("camera_frame_ids"),list)
            or len(summary["camera_frame_ids"])!=len(pose)
            or len(set(summary["camera_frame_ids"]))!=len(pose)
            or any(not isinstance(x,str) or not x for x in summary["camera_frame_ids"])):
        raise ValueError("inconsistent calibrated camera/observation identities")
    network=RGBUnscaledNetwork(
        tuple(summary["camera_frame_ids"]),
        tuple(p.copy() for p in pose),
        len(points),len(points),0,0.,0.,
        landmark_xyz_unit_baseline=points,
        observation_landmark_indices=lid,
        observation_frame_indices=fid,
        observation_pixels_xy=xy,
    )
    intrinsics=PinholeIntrinsics(float(k[0]),float(k[1]),float(k[2]),float(k[3]))
    result=adjust_windowed_unscaled_rgb_network(network,intrinsics)
    dest_npz=target/"rgb-global-windowed-ba-unscaled.npz"
    dest_json=target/"rgb-global-windowed-ba-unscaled.json"
    created=[]
    try:
        with dest_npz.open("xb") as fp:
            created.append(dest_npz)
            np.savez_compressed(
                fp,
                poses_world_to_camera_arbitrary=np.stack(result.world_to_camera),
                landmarks_xyz_arbitrary=result.landmark_xyz_unit_baseline,
                observation_landmark_indices=lid,
                observation_frame_indices=fid,
                observation_pixels_xy=xy,
                calibrated_intrinsics=k,
            )
        metadata={
            "schema":"mcm.rgb_global_windowed_ba.v1",
            "status":result.status,
            "source_3d_geometry_not_metric":True,
            "camera_count":result.camera_count,
            "landmark_count":result.landmark_count,
            "observation_count":result.observation_count,
            "window_count":result.completed_windows,
            "rmse_before_px":result.before_rmse_px,
            "rmse_after_px":result.after_rmse_px,
            "p95_before_px":result.before_p95_px,
            "p95_after_px":result.after_p95_px,
            "result_npz":dest_npz.name,
            "camera_frame_ids":list(network.frame_ids),
            "global_joint_ba_completed":False,
            "metric_scale_verified":False,
            "georeferencing_verified":False,
            "orthophoto_verified":False,
            "pv_module_detection_performed":False,
        }
        with dest_json.open("x",encoding="utf-8") as fp:
            created.append(dest_json)
            json.dump(metadata,fp,sort_keys=True,indent=2)
            fp.write("\n")
    except BaseException:
        for f in created:
            f.unlink(missing_ok=True)
        raise
    print(json.dumps({
        "status":result.status,
        "camera_count":result.camera_count,
        "windows":result.completed_windows,
        "orthophoto_verified":False,
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
