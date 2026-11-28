"""Whole imported project -> bounded ORB tracks -> unscaled global camera network.

No ODM, external subprocesses, automatic metric calibration or database writes.
"""
from __future__ import annotations

import cv2
import numpy as np

from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_project_roof_vertical import _project_rgb_frames
from mcm_solarcheck.services.orthomosaic_overlap_candidates import select_overlap_candidates
from mcm_solarcheck.services.rgb_global_camera_network import (
    RGBNetworkFrame, RGBNetworkLink, solve_global_rgb_camera_network,
)


def reconstruct_project_rgb_camera_network(
    database, project_id, calibration, *,
    max_frames=1000, max_side=1200, max_features=2000,
    should_cancel=None, on_progress=None,
):
    """All imported RGB images or fail; no silent flight-segment sampling."""
    def cancel():
        if should_cancel is not None and should_cancel():
            raise RuntimeError("RGB camera network cancelled")
    cancel()
    if (not isinstance(calibration,dict) or
        calibration.get("schema")!="mcm.rgb_camera_intrinsics_external.v1" or
        calibration.get("lens_calibration_verified") is not True or
        not isinstance(calibration.get("calibration_provenance"),str) or
        not calibration["calibration_provenance"].strip()):
        raise ValueError("independently calibrated camera model required")
    try:
        k=calibration["intrinsics"]
        intrinsics=PinholeIntrinsics(k["fx"],k["fy"],k["cx"],k["cy"])
        distortion=np.asarray(calibration["distortion_coefficients"],dtype=np.float64)
    except (ValueError,KeyError,TypeError) as error:
        raise ValueError("complete calibrated lens coefficients required") from error
    if distortion.shape not in ((4,),(5,),(8,),(12,),(14,)) or not np.isfinite(distortion).all():
        raise ValueError("finite calibrated distortion coefficients required")
    if (type(max_side) is not int or not 256<=max_side<=2400 or
        type(max_features) is not int or not 300<=max_features<=4000):
        raise ValueError("bounded ORB processing budgets required")
    records=_project_rgb_frames(database,project_id,max_frames=max_frames)
    width,height=records[0][2:]
    if any((row[2],row[3])!=(width,height) for row in records):
        raise ValueError("mixed sensor dimensions need separate camera calibration")
    if not 0<=intrinsics.cx<width or not 0<=intrinsics.cy<height:
        raise ValueError("calibration principal point outside RGB image")
    matrix=np.array(((intrinsics.fx,0.,intrinsics.cx),
                    (0.,intrinsics.fy,intrinsics.cy),(0.,0.,1.)),dtype=np.float64)
    if not np.isfinite(matrix).all() or intrinsics.fx<=0 or intrinsics.fy<=0:
        raise ValueError("finite positive calibrated focal lengths required")
    orb=cv2.ORB_create(nfeatures=max_features)
    observations=[]
    descriptors=[]
    for idx,(fid,path,w,h) in enumerate(records):
        cancel()
        # Decode one full primary frame at a time, then discard its buffer.
        image=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
        if image is None or image.shape!=(h,w):
            raise ValueError("unreadable imported primary RGB original")
        scale=min(1.,max_side/max(w,h))
        if scale<1:
            image=cv2.resize(image,(max(32,round(w*scale)),max(32,round(h*scale))),
                             interpolation=cv2.INTER_AREA)
        actual_x=image.shape[1]/w
        actual_y=image.shape[0]/h
        k_small=matrix.copy()
        k_small[0,:]*=actual_x
        k_small[1,:]*=actual_y
        image=cv2.undistort(image,k_small,distortion,None,k_small)
        keypoints,desc=orb.detectAndCompute(image,None)
        if desc is None or len(keypoints)<16:
            raise ValueError("RGB image lacks sufficient common 2D image features")
        xy=np.float64([(p.pt[0]/actual_x,p.pt[1]/actual_y) for p in keypoints])
        observations.append(RGBNetworkFrame(fid,xy))
        descriptors.append(desc)
        if on_progress is not None:
            on_progress("features",idx+1,len(records))
    ids=tuple(row[0] for row in records)
    cross=tuple((ids[i],ids[i+step])
                for step in (2,4) for i in range(len(ids)-step))
    candidates=select_overlap_candidates(ids,cross_strip_pairs=cross,max_candidates=4000)
    matcher=cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True)
    links=[]
    for idx,pair in enumerate(candidates):
        cancel()
        i,j=ids.index(pair.first_id),ids.index(pair.second_id)
        matches=sorted(matcher.match(descriptors[i],descriptors[j]),key=lambda m:m.distance)
        matches=[m for m in matches if m.distance<=64]
        if len(matches)>=8:
            links.append(RGBNetworkLink(
                pair.first_id,pair.second_id,
                np.int32([(m.queryIdx,m.trainIdx) for m in matches]),
            ))
        if on_progress is not None:
            on_progress("links",idx+1,len(candidates))
    cancel()
    return solve_global_rgb_camera_network(
        tuple(observations),tuple(links),intrinsics,
        should_cancel=should_cancel,
    )
