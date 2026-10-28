"""Calibrated, *unscaled* global 3D RGB camera network from multi-image tracks.

Reuses the existing project RGB inventory and OpenCV ORB feature matching.
All photos form one network: feature links are merged into consistent tracks,
essential geometry initializes cameras, 3D track landmarks seed PnP for further
views, and every posed image participates in a global reprojection audit.

IMPORTANT: The first camera pair fixes an *arbitrary unit baseline*. Neither a
true metric scale nor roof geometry/CRS can be inferred from this output. This
is an SfM INITIALIZATION, not bundle adjustment or an orthophoto. NEVER feed
these unscaled cameras to the verified metric roof tile renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import numpy as np
import cv2

from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics


@dataclass(frozen=True)
class RGBNetworkFrame:
    frame_id: str
    points_xy: np.ndarray  # undistorted pixels in original sensor coordinates


@dataclass(frozen=True)
class RGBNetworkLink:
    first_id: str
    second_id: str
    feature_indices: np.ndarray  # Nx2, ORB cross-check matches


@dataclass(frozen=True)
class RGBUnscaledNetwork:
    frame_ids: tuple[str, ...]
    world_to_camera: tuple[np.ndarray, ...]  # arbitrary unit baseline
    reconstructed_landmarks: int
    multiview_tracks: int
    linked_image_pairs: int
    reprojection_p95_px: float
    reprojection_max_px: float
    state: str = "global_sfm_initialization_unscaled_unverified"
    metric_scale_verified: bool = False
    roof_geometry_verified: bool = False
    orthophoto_verified: bool = False
    bundle_adjustment_completed: bool = False
    # Internal, UNMETRIC optimization payload; not approved roof geometry.
    landmark_xyz_unit_baseline: np.ndarray | None = None
    observation_landmark_indices: np.ndarray | None = None
    observation_frame_indices: np.ndarray | None = None
    observation_pixels_xy: np.ndarray | None = None
    # Pairs that survived calibrated essential-matrix RANSAC and pose recovery;
    # these are geometric link candidates, NOT independent roof/strip proof.
    accepted_link_pairs: tuple[tuple[str, str], ...] = ()


def _project(pose, point, k):
    camera = pose[:, :3] @ point + pose[:, 3]
    if camera[2] <= 1.e-8 or not np.isfinite(camera).all():
        return None
    return np.array((k[0,0] * camera[0] / camera[2] + k[0,2],
                     k[1,1] * camera[1] / camera[2] + k[1,2]))


def _triangulate(track, poses, frames, k, *, max_reprojection_px):
    seen = [(index, frames[index].points_xy[idx]) for index, idx in track.items()
            if index in poses]
    if len(seen) < 2:
        return None
    # Prefer maximum known baseline (the best separated viewing geometry).
    scored = []
    for a in range(len(seen)):
        for b in range(a + 1, len(seen)):
            i, p_i = seen[a]
            j, p_j = seen[b]
            ca = -poses[i][:, :3].T @ poses[i][:, 3]
            cb = -poses[j][:, :3].T @ poses[j][:, 3]
            scored.append((float(np.linalg.norm(cb - ca)), i, p_i, j, p_j))
    distance, i, pi, j, pj = max(scored, key=lambda row: row[0])
    if distance < 1e-5:
        return None
    first = k @ poses[i]
    second = k @ poses[j]
    homog = cv2.triangulatePoints(first, second, np.asarray(pi).reshape(2,1),
                                  np.asarray(pj).reshape(2,1)).reshape(4)
    if not np.isfinite(homog).all() or abs(homog[3]) < 1e-10:
        return None
    xyz = homog[:3] / homog[3]
    # Require all camera observations to be in front and within the pixel gate.
    for index, observed in seen:
        fitted = _project(poses[index], xyz, k)
        if fitted is None or float(np.linalg.norm(fitted - observed)) > max_reprojection_px:
            return None
    # Reject extremely far/low-parallax intersections: their arbitrary
    # baseline cannot yield a stable triangulation.
    c1 = -poses[i][:,:3].T @ poses[i][:,3]
    c2 = -poses[j][:,:3].T @ poses[j][:,3]
    u, v = xyz - c1, xyz - c2
    angle_sine = np.linalg.norm(np.cross(u,v)) / (np.linalg.norm(u)*np.linalg.norm(v))
    if not np.isfinite(angle_sine) or angle_sine < .012:
        return None
    return xyz


def solve_global_rgb_camera_network(
    frames: tuple[RGBNetworkFrame, ...],
    links: tuple[RGBNetworkLink, ...],
    intrinsics: PinholeIntrinsics,
    *,
    min_inliers: int = 12,
    max_reprojection_px: float = 3.0,
    max_frames: int = 1000,
    max_track_count: int = 40000,
    should_cancel=None,
) -> RGBUnscaledNetwork:
    """Use all supplied frames; never return a partial or metric camera network.

    A successful return implies 3+ globally connected, posed images and
    common 3D tracks. Geometry remains scale-free until independent GCPs fix
    the datum and a separate bundle-adjustment/validation gate is passed.
    """
    def cancel():
        if should_cancel is not None and should_cancel():
            raise RuntimeError("RGB global camera network cancelled")
    cancel()
    if (type(frames) is not tuple or not 3 <= len(frames) <= max_frames <= 1000
            or type(links) is not tuple or type(max_track_count) is not int
            or not 100 <= max_track_count <= 200000
            or type(min_inliers) is not int or not 8 <= min_inliers <= 1000
            or not isfinite(max_reprojection_px) or not 0 < max_reprojection_px <= 10):
        raise ValueError("bounded three-or-more-frame RGB network required")
    frame_ids = tuple(f.frame_id for f in frames)
    if (any(not isinstance(f, RGBNetworkFrame) or not isinstance(f.frame_id, str)
            or not f.frame_id for f in frames) or len(set(frame_ids)) != len(frames)):
        raise ValueError("unique valid RGB image identities required")
    ids = {name: i for i, name in enumerate(frame_ids)}
    focal = (intrinsics.fx, intrinsics.fy, intrinsics.cx, intrinsics.cy)
    if any(type(x) not in (float, int) or not isfinite(x) for x in focal) or min(focal[:2]) <= 0:
        raise ValueError("finite independently calibrated camera intrinsics required")
    k = np.array(((focal[0],0.,focal[2]),(0.,focal[1],focal[3]),(0.,0.,1.)),dtype=np.float64)
    for frame in frames:
        xy = frame.points_xy
        if (not isinstance(xy, np.ndarray) or xy.dtype not in (np.float32,np.float64)
                or xy.ndim != 2 or xy.shape[1] != 2 or not 8 <= len(xy) <= 10000
                or not np.isfinite(xy).all()):
            raise ValueError("bounded undistorted RGB feature points required")
    # Union-find merges only if a candidate track has no duplicate frame.
    parent, owners = {}, {}
    def find(node):
        if node not in parent:
            parent[node] = node
            owners[node] = {node[0]:node[1]}
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node
    def join(a,b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if owners[ra].keys() & owners[rb].keys():
            return
        if len(owners[ra]) < len(owners[rb]):
            ra,rb = rb,ra
        parent[rb] = ra
        owners[ra].update(owners.pop(rb))
    accepted = []
    used_pairs = set()
    for link in links:
        cancel()
        if (not isinstance(link, RGBNetworkLink) or link.first_id not in ids
                or link.second_id not in ids or link.first_id == link.second_id):
            raise ValueError("network link references unknown or duplicate image")
        i,j = ids[link.first_id],ids[link.second_id]
        key = frozenset((i,j))
        if key in used_pairs:
            raise ValueError("duplicate inter-camera network link")
        used_pairs.add(key)
        indices = link.feature_indices
        if (not isinstance(indices,np.ndarray) or indices.ndim != 2 or indices.shape[1] != 2
                or not np.issubdtype(indices.dtype, np.integer)
                or len(indices) < 8 or len(indices) > 10000
                or np.any(indices < 0) or np.any(indices[:,0] >= len(frames[i].points_xy))
                or np.any(indices[:,1] >= len(frames[j].points_xy))):
            raise ValueError("bounded valid feature correspondence indices required")
        if len(set(map(tuple,indices.tolist()))) != len(indices):
            raise ValueError("duplicate feature correspondence in RGB pair")
        pi,pj = frames[i].points_xy[indices[:,0]], frames[j].points_xy[indices[:,1]]
        e,mask = cv2.findEssentialMat(pi,pj,k,cv2.RANSAC,0.999,max_reprojection_px)
        if e is None or mask is None or len(e) < 3:
            continue
        e = e[:3,:]
        count,r,t,pose_mask = cv2.recoverPose(e,pi,pj,k,mask=mask)
        chosen = indices[np.asarray(pose_mask).reshape(-1)!=0]
        if count < min_inliers or len(chosen) < min_inliers:
            continue
        accepted.append((i,j,r,t.reshape(3),chosen))
    if not accepted:
        raise ValueError("no calibrated multi-image essential geometry")
    # All pair links feed one GLOBAL track graph, not separate mosaics.
    for i,j,_,_,match_indices in sorted(accepted,key=lambda v:-len(v[4])):
        for a,b in match_indices:
            join((i,int(a)),(j,int(b)))
            if len(parent)>max_track_count*5:
                raise ValueError("RGB feature graph exceeds track resource budget")
    tracks = list(owners.values())
    if len(tracks)>max_track_count:
        raise ValueError("RGB network exceeds landmark budget")
    multi = [track for track in tracks if len(track)>=3]
    if len(multi)<min_inliers:
        raise ValueError("insufficient shared three-view RGB feature tracks")

    # Anchor one arbitrary baseline. No external scale or world datum!
    roots=[v for v in accepted if v[0]==0 or v[1]==0]
    if not roots:
        raise ValueError("first camera lacks calibrated network baseline")
    first=max(roots,key=lambda x:len(x[4]))
    i,j,r,t,_=first
    identity=np.column_stack((np.eye(3),np.zeros(3)))
    if i==0:
        other=j
        second=np.column_stack((r,t))
    else:
        other=i
        inv_r=r.T
        second=np.column_stack((inv_r,-inv_r@t))
    poses={0:identity,other:second}
    landmarks={}
    def retriangulate():
        for index,track in enumerate(tracks):
            cancel()
            if len(track)<2:
                continue
            xyz=_triangulate(track,poses,frames,k,max_reprojection_px=max_reprojection_px)
            if xyz is not None:
                landmarks[index]=xyz
            else:
                landmarks.pop(index,None)
    retriangulate()
    for _ in range(len(frames)-2):
        cancel()
        if len(poses)==len(frames):
            break
        candidates=[]
        for frame_index in range(len(frames)):
            if frame_index in poses:
                continue
            correspondences=[
                (landmarks[index],frames[frame_index].points_xy[track[frame_index]])
                for index,track in enumerate(tracks) if frame_index in track and index in landmarks
            ]
            if len(correspondences)>=min_inliers:
                candidates.append((len(correspondences),frame_index,correspondences))
        if not candidates:
            break
        _,frame_index,observations=max(candidates,key=lambda item:item[0])
        xyz=np.array([x for x,_ in observations],dtype=np.float64)
        pixels=np.array([y for _,y in observations],dtype=np.float64)
        success,rot,translation,inliers=cv2.solvePnPRansac(
            xyz,pixels,k,None,iterationsCount=300,
            reprojectionError=max_reprojection_px,confidence=.999,
            flags=cv2.SOLVEPNP_EPNP,
        )
        if not success or inliers is None or len(inliers)<min_inliers:
            raise ValueError("global camera PnP pose has insufficient 3D support")
        selected=inliers.reshape(-1)
        rot,translation=cv2.solvePnPRefineLM(xyz[selected],pixels[selected],k,None,rot,translation)
        matrix=np.column_stack((cv2.Rodrigues(rot)[0],translation.reshape(3)))
        if not np.isfinite(matrix).all():
            raise ValueError("nonfinite RGB network camera pose")
        poses[frame_index]=matrix
        retriangulate()
    if len(poses)!=len(frames):
        raise ValueError("disconnected or underconstrained RGB camera network")
    errors=[]
    participating=set()
    supported={index:0 for index in range(len(frames))}
    for index,point in landmarks.items():
        track=tracks[index]
        for frame_index,feature_index in track.items():
            fit=_project(poses[frame_index],point,k)
            if fit is None:
                continue
            error=float(np.linalg.norm(fit-frames[frame_index].points_xy[feature_index]))
            if error<=max_reprojection_px:
                errors.append(error)
                supported[frame_index]+=1
                participating.add(frame_index)
    # A camera with just one lucky track cannot pass the all-frame gate.
    if (len(errors)<min_inliers*3 or len(participating)!=len(frames)
            or any(value<min_inliers for value in supported.values())):
        raise ValueError("incomplete global RGB reprojection evidence")
    p95=float(np.percentile(errors,95))
    if not np.isfinite(p95) or p95>max_reprojection_px:
        raise ValueError("inconsistent global RGB reprojection error")
    # Retain the shared landmark/observation bundle for the NEXT global BA
    # without another expensive original-image decode / ORB matching pass.
    xyz_points=[]
    obs_landmark=[]
    obs_frame=[]
    obs_pixels=[]
    for old_track_index,xyz in sorted(landmarks.items()):
        new_id=len(xyz_points)
        xyz_points.append(xyz)
        for frame_index,feature_index in sorted(tracks[old_track_index].items()):
            observed=frames[frame_index].points_xy[feature_index]
            fitted=_project(poses[frame_index],xyz,k)
            if fitted is not None and np.linalg.norm(fitted-observed)<=max_reprojection_px:
                obs_landmark.append(new_id)
                obs_frame.append(frame_index)
                obs_pixels.append(observed)
    arrays=(
        np.asarray(xyz_points,dtype=np.float64).reshape(-1,3),
        np.asarray(obs_landmark,dtype=np.int32),
        np.asarray(obs_frame,dtype=np.int32),
        np.asarray(obs_pixels,dtype=np.float64).reshape(-1,2),
    )
    for array in arrays:
        array.setflags(write=False)
    return RGBUnscaledNetwork(
        frame_ids,tuple(poses[i] for i in range(len(frames))),
        len(landmarks),len(multi),len(accepted),p95,max(errors),
        landmark_xyz_unit_baseline=arrays[0],
        observation_landmark_indices=arrays[1],
        observation_frame_indices=arrays[2],
        observation_pixels_xy=arrays[3],
        accepted_link_pairs=tuple(
            (frame_ids[i], frame_ids[j]) for i, j, _, _, _ in accepted
        ),
    )
