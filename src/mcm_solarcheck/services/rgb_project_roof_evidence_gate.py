"""Bind unverified ENU SfM cameras to a real, read-only SolarCheck RGB project.

Bridge the prior RGB ENU-candidate stage with the EXISTING surveyed-plane
ray projection and roof-tile plan. All imported project RGB frames MUST be
present and have independently observed rooftop hold-outs. No RGB pixels are
read, no SQLite writes, no claimed authenticated survey or orthophoto.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import numpy as np

from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D,
    project_pixels_to_surveyed_plane,
)
from mcm_solarcheck.services.module_plane_basis import (
    basis_from_surveyed_plane, plane_coordinates,
)
from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid
from mcm_solarcheck.services.rgb_surface_tiles import plan_rgb_surface_tiles
from mcm_solarcheck.services.rgb_project_roof_vertical import _project_rgb_frames


@dataclass(frozen=True)
class RGBProjectRoofEvidenceAudit:
    source_count: int
    rooftop_holdout_count: int
    largest_per_camera_error_m: float
    p95_rooftop_error_m: float
    candidate_tile_count: int
    state: str = "project_roof_geometry_consistent_expert_review_required"
    survey_authenticity_verified: bool = False
    camera_calibration_independently_verified: bool = False
    eligible_for_verified_roof_tiles: bool = False
    metric_scale_verified: bool = False
    georeferencing_verified: bool = False
    orthophoto_verified: bool = False


def screen_project_rgb_roof_geometry(
    database, project_id,
    candidate_manifest: dict, candidate_arrays: dict,
    gcp_survey: dict, roof_survey: dict,
    *, max_frames: int = 1000, should_cancel=None,
) -> RGBProjectRoofEvidenceAudit:
    """Check ENU ray-plane errors for EACH imported primary RGB photograph.

    Numeric consistency is not independent authentication of calibration,
    survey, datum, image point identity or physical roof geometry. This
    function CANNOT turn candidate georeferencing into a release authority.
    """
    def cancel():
        if should_cancel is not None and should_cancel():
            raise RuntimeError("RGB project roof evidence check cancelled")
    cancel()
    if not isinstance(candidate_manifest, dict) or candidate_manifest.get(
            "schema") != "mcm.rgb_camera_enu_candidate.v1":
        raise ValueError("ENU candidate manifest required")
    mandatory_false = (
        "survey_evidence_authenticity_verified", "metric_scale_verified",
        "georeferencing_verified", "roof_plane_verified",
        "eligible_for_verified_roof_tiles", "orthophoto_verified",
    )
    if any(candidate_manifest.get(flag) is not False for flag in mandatory_false):
        raise ValueError("cannot use verified or incomplete ENU candidate state")
    if not isinstance(gcp_survey, dict) or gcp_survey.get(
            "schema") != "mcm.rgb_independent_enu_controls.v1":
        raise ValueError("original fitting/hold-out GCP evidence required")
    if not isinstance(roof_survey, dict) or roof_survey.get(
            "schema") != "mcm.rgb_project_roof_holdouts.v1":
        raise ValueError("project-specific independently measured roof hold-outs required")
    if roof_survey.get("project_id") != project_id:
        raise ValueError("roof survey belongs to another SolarCheck project")
    calibration = roof_survey.get("calibration_evidence")
    if (not isinstance(calibration, dict)
            or calibration.get("undistorted_pixel_coordinates") is not True
            or not isinstance(calibration.get("calibration_reference"), str)
            or not calibration["calibration_reference"].strip()
            or not isinstance(calibration.get("roof_survey_reference"), str)
            or not calibration["roof_survey_reference"].strip()):
        raise ValueError("external calibrated undistorted pixel and roof survey references required")
    # References name external evidence, but cannot authenticate it.
    frames = _project_rgb_frames(database, project_id, max_frames=max_frames)
    frame_ids = tuple(row[0] for row in frames)
    labels = candidate_manifest.get("camera_frame_ids")
    if (type(labels) is not list or labels != list(frame_ids)
            or not isinstance(candidate_arrays, dict)):
        raise ValueError("ENU candidate must cover EVERY imported project RGB image in order")
    keys = {"camera_centers_enu_candidate_m","camera_to_enu_candidate",
            "landmarks_enu_candidate_m","intrinsics_undistorted_pixels"}
    if set(candidate_arrays) != keys:
        raise ValueError("complete explicit ENU camera array package required")
    centers=np.asarray(candidate_arrays["camera_centers_enu_candidate_m"])
    rotations=np.asarray(candidate_arrays["camera_to_enu_candidate"])
    landmarks=np.asarray(candidate_arrays["landmarks_enu_candidate_m"])
    intrinsics=np.asarray(candidate_arrays["intrinsics_undistorted_pixels"])
    count=len(frames)
    if (centers.shape != (count,3) or rotations.shape != (count,3,3)
            or landmarks.ndim != 2 or landmarks.shape[1] != 3
            or intrinsics.shape != (4,)
            or any(a.dtype.kind not in "fiu" or not np.isfinite(a).all()
                   for a in (centers,rotations,landmarks,intrinsics))
            or intrinsics[0] <= 0 or intrinsics[1] <= 0):
        raise ValueError("finite complete bounded ENU camera candidate geometry required")
    if len(landmarks) < 8 or len(landmarks) > 200000:
        raise ValueError("ENU candidate landmark resource budget exceeded")
    for rot in rotations:
        if (not np.allclose(rot.T@rot,np.eye(3),atol=1e-5)
                or not np.isclose(np.linalg.det(rot),1.,atol=1e-5)):
            raise ValueError("ENU candidate camera rotation must be proper")
    if any(not 0<=intrinsics[2]<w or not 0<=intrinsics[3]<h
           for _,_,w,h in frames):
        raise ValueError("camera principal point outside imported RGB frames")
    try:
        plane_data=roof_survey["plane"]
        plane=SurveyedPlane3D(
            tuple(plane_data["point_enu_m"]),tuple(plane_data["normal_enu"])
        )
        grid=roof_survey["grid"]
        plan=plan_rgb_surface_tiles(
            ModuleSurfaceGrid(
                grid["u_min_m"],grid["v_min_m"],grid["metres_per_pixel"],
                grid["width"],grid["height"],
            ),
            tile_side_px=grid["tile_side_px"],
            max_total_pixels=12_000_000,max_tiles=64,
        )
        limit=roof_survey["allowed_rooftop_error_m"]
        points=roof_survey["controls"]
    except (KeyError,TypeError,ValueError,OverflowError) as error:
        raise ValueError("explicit surveyed plane, tile grid and roof controls required") from error
    if (type(limit) not in (int,float) or not isfinite(limit)
            or not 0<limit<=2):
        raise ValueError("positive bounded independent roof residual tolerance required")
    if type(points) is not list or not 4*count <= len(points) <= 100*count:
        raise ValueError("at least four independent roof controls per imported RGB required")
    training=gcp_survey.get("fit_controls")
    held_out=gcp_survey.get("holdout_controls")
    if not isinstance(training,list) or not isinstance(held_out,list):
        raise ValueError("separate original ENU GCP train/holdout registers required")
    gcp_ids=set()
    gcp_xyz=[]
    for group in (training,held_out):
        if len(group)<4:
            raise ValueError("original independent GCP register is incomplete")
        for item in group:
            if not isinstance(item,dict) or not isinstance(item.get("control_id"),str):
                raise ValueError("invalid original GCP identifiers")
            if item["control_id"] in gcp_ids:
                raise ValueError("duplicate original GCP identifiers")
            gcp_ids.add(item["control_id"])
            try:
                xyz=np.asarray(item["point_enu_m"],dtype=np.float64)
            except (KeyError,TypeError,ValueError) as error:
                raise ValueError("invalid original GCP coordinate") from error
            if xyz.shape != (3,) or not np.isfinite(xyz).all():
                raise ValueError("finite original ENU GCP coordinate required")
            gcp_xyz.append(xyz)
    gcp_xyz=np.stack(gcp_xyz)
    basis=basis_from_surveyed_plane(plane)
    k=PinholeIntrinsics(*(float(v) for v in intrinsics))
    by_frame={f:[] for f in frame_ids}
    seen=set()
    for p in points:
        cancel()
        if not isinstance(p,dict):
            raise ValueError("explicit independent roof control required")
        fid=p.get("frame_id")
        key=p.get("control_id")
        if (fid not in by_frame or not isinstance(key,str) or not key.strip()
                or key in gcp_ids or (fid,key) in seen
                or p.get("used_in_3d_gcp_fit") is not False):
            raise ValueError("roof controls must be unique and disjoint from fitted GCPs")
        seen.add((fid,key))
        try:
            pixel=np.asarray(p["undistorted_pixel_xy"],dtype=np.float64)
            enu=np.asarray(p["surveyed_point_enu_m"],dtype=np.float64)
        except (KeyError,ValueError,TypeError) as error:
            raise ValueError("finite observed roof control coordinates required") from error
        if (pixel.shape != (2,) or enu.shape != (3,)
                or not np.isfinite(pixel).all() or not np.isfinite(enu).all()
                or np.any(np.linalg.norm(gcp_xyz-enu,axis=1) < 1e-5)):
            raise ValueError("roof control coordinates invalid or reused from GCP")
        by_frame[fid].append((pixel,enu))
    errors=[]
    for index,(_,_,width,height) in enumerate(frames):
        cancel()
        obs=by_frame[frame_ids[index]]
        if not 4<=len(obs)<=100:
            raise ValueError("each imported RGB camera requires four independent roof controls")
        pixels=np.stack([p for p,_ in obs])
        ground=np.stack([g for _,g in obs])
        if (np.any(pixels<0) or np.any(pixels[:,0]>=width-1)
                or np.any(pixels[:,1]>=height-1)):
            raise ValueError("independent roof pixel observation outside original RGB")
        actual_uv=plane_coordinates(ground,basis,tolerance_m=float(limit))
        if np.min(np.ptp(actual_uv,axis=0))<.2:
            raise ValueError("rooftop hold-outs insufficiently distributed")
        sv=np.linalg.svd(actual_uv-actual_uv.mean(axis=0),compute_uv=False)
        if sv[0] <= 0 or sv[-1]/sv[0]<.05:
            raise ValueError("rooftop hold-outs cannot be collinear")
        extrinsics=CameraExtrinsicsENU(
            tuple(float(v) for v in centers[index]),
            tuple(tuple(float(v) for v in row) for row in rotations[index]),
        )
        projection=project_pixels_to_surveyed_plane(pixels,k,extrinsics,plane)
        image_uv=plane_coordinates(projection,basis)
        distances=np.linalg.norm(image_uv-actual_uv,axis=1)
        if not np.isfinite(distances).all() or float(np.max(distances))>limit:
            raise ValueError("independent per-frame roof control residual exceeds declared tolerance")
        errors.extend(float(x) for x in distances)
    return RGBProjectRoofEvidenceAudit(
        count,len(errors),float(np.max(errors)),float(np.percentile(errors,95)),
        len(plan.tiles),
    )
