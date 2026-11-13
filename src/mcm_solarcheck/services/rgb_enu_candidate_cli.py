"""Unscaled whole-flight BA NPZ + independent survey -> local ENU CANDIDATE.

Offline, bounded, read-only inputs. Outputs only into a chosen EMPTY folder.
The candidate never claims authenticated survey, verified metric coordinates,
approved roof plane or orthophoto. These require independent expert gates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

import numpy as np

from mcm_solarcheck.services.rgb_enu_ground_control_gate import (
    RGBSurveyed3DControl, fit_enu_candidate_from_survey,
)


def _regular_bounded(path, max_bytes):
    path = Path(path)
    if (not path.is_file() or path.is_symlink() or
            path.stat().st_size > max_bytes):
        raise ValueError("existing bounded regular local survey input required")
    return path


def _controls(rows, label):
    if not isinstance(rows, list) or not 4 <= len(rows) <= 1000:
        raise ValueError("four or more external survey controls required")
    controls=[]
    for item in rows:
        try:
            controls.append(RGBSurveyed3DControl(
                item["control_id"], item["landmark_index"],
                tuple(item["point_enu_m"]),
            ))
        except (KeyError,TypeError,ValueError) as error:
            raise ValueError(f"invalid external {label} control") from error
    return tuple(controls)


def main(argv=None):
    parser=argparse.ArgumentParser(
        description="Independent GCP + holdout fit (candidate ENU, NOT verified ortho)",
    )
    parser.add_argument("--ba-npz",required=True)
    parser.add_argument("--ba-json",required=True)
    parser.add_argument("--survey-json",required=True)
    parser.add_argument("--output-directory",required=True)
    args=parser.parse_args(argv)
    source=_regular_bounded(args.ba_npz,50_000_000)
    metadata=_regular_bounded(args.ba_json,1_000_000)
    survey=_regular_bounded(args.survey_json,2_000_000)
    out=Path(args.output_directory)
    if not out.is_dir() or out.is_symlink() or any(out.iterdir()):
        raise ValueError("existing empty local ENU candidate output directory required")
    if len({p.resolve() for p in (source,metadata,survey)})!=3:
        raise ValueError("separate NPZ, BA manifest and independent survey files required")
    target=out.resolve()
    for p in (source,metadata,survey):
        resolved=p.resolve()
        if target==resolved.parent or target in resolved.parents:
            raise ValueError("cannot place candidate output over external survey sources")
    info=json.loads(metadata.read_text(encoding="utf-8"))
    points_info=json.loads(survey.read_text(encoding="utf-8"))
    if (not isinstance(info,dict)
            or info.get("schema")!="mcm.rgb_global_windowed_ba.v1"
            or info.get("result_npz")!=source.name
            or info.get("source_3d_geometry_not_metric") is not True
            or info.get("metric_scale_verified") is not False
            or info.get("georeferencing_verified") is not False
            or info.get("orthophoto_verified") is not False
            or info.get("global_joint_ba_completed") is not False):
        raise ValueError("explicitly unscaled whole-project BA manifest required")
    if (not isinstance(points_info,dict)
            or points_info.get("schema")!="mcm.rgb_independent_enu_controls.v1"):
        raise ValueError("independently surveyed ENU control package required")
    with zipfile.ZipFile(source) as archive:
        members=archive.infolist()
        if (len(members)>12
                or any(m.file_size>50_000_000 for m in members)
                or sum(m.file_size for m in members)>100_000_000):
            raise ValueError("untrusted oversized unscaled SfM archive")
    with np.load(source,allow_pickle=False) as data:
        required={
            "poses_world_to_camera_arbitrary",
            "landmarks_xyz_arbitrary",
            "observation_landmark_indices",
            "observation_frame_indices",
            "observation_pixels_xy",
            "calibrated_intrinsics",
        }
        if set(data.files)!=required:
            raise ValueError("complete saved unscaled global BA network required")
        pose=data["poses_world_to_camera_arbitrary"]
        landmark=data["landmarks_xyz_arbitrary"]
        k=data["calibrated_intrinsics"]
    frame_ids=info.get("camera_frame_ids")
    if (k.shape!=(4,) or not np.isfinite(k).all()
            or not isinstance(frame_ids,list) or len(frame_ids)!=len(pose)
            or len(set(frame_ids))!=len(frame_ids)
            or any(not isinstance(v,str) or not v for v in frame_ids)):
        raise ValueError("inconsistent camera identity or calibrated intrinsics")
    training=_controls(points_info.get("fit_controls"),"fitting")
    held_out=_controls(points_info.get("holdout_controls"),"held-out")
    result=fit_enu_candidate_from_survey(
        pose,landmark,training,held_out,
        fit_survey_provenance=points_info.get("fit_survey_provenance"),
        holdout_survey_provenance=points_info.get("holdout_survey_provenance"),
        allowed_max_error_m=points_info.get("allowed_max_error_m"),
        minimum_spread_m=points_info.get("minimum_spread_m",.5),
    )
    # No conversion to VerifiedCameraGeometry / automatic roof-plane export:
    # supplying text-only "provenance" is NOT independent authentication.
    candidate_npz=out/"rgb-camera-enu-candidate-unverified.npz"
    candidate_json=out/"rgb-camera-enu-candidate-unverified.json"
    created=[]
    try:
        with candidate_npz.open("xb") as f:
            created.append(candidate_npz)
            np.savez_compressed(
                f,
                camera_centers_enu_candidate_m=np.asarray([
                    c.center_enu_m for c in result.camera_extrinsics_candidate
                ],dtype=np.float64),
                camera_to_enu_candidate=np.asarray([
                    c.camera_to_enu for c in result.camera_extrinsics_candidate
                ],dtype=np.float64),
                landmarks_enu_candidate_m=result.landmark_points_enu_candidate_m,
                intrinsics_undistorted_pixels=k,
            )
        summary={
            "schema":"mcm.rgb_camera_enu_candidate.v1",
            "state":result.state,
            "source_global_ba_npz":source.name,
            "candidate_npz":candidate_npz.name,
            "camera_frame_ids":frame_ids,
            "fit_control_count":result.fit_control_count,
            "holdout_control_count":result.held_out_control_count,
            "fit_max_residual_m":result.fit_max_error_m,
            "holdout_max_residual_m":result.holdout_max_error_m,
            "holdout_p95_residual_m":result.holdout_p95_error_m,
            "scale_m_per_arbitrary_unit":result.scale_m_per_arbitrary_unit,
            "survey_evidence_authenticity_verified":False,
            "metric_scale_verified":False,
            "georeferencing_verified":False,
            "roof_plane_verified":False,
            "eligible_for_verified_roof_tiles":False,
            "orthophoto_verified":False,
            "pv_module_detection_performed":False,
            "thermal_registration_verified":False,
        }
        with candidate_json.open("x",encoding="utf-8") as f:
            created.append(candidate_json)
            json.dump(summary,f,indent=2,sort_keys=True)
            f.write("\n")
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    print(json.dumps({
        "status":result.state,
        "cameras":len(frame_ids),
        "held_out_controls":result.held_out_control_count,
        "orthophoto_verified":False,
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
