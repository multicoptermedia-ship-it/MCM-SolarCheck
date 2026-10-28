"""Bounded GLOBAL reprojection bundle adjustment on an existing SfM track bundle.

Levenberg-Marquardt with per-landmark Schur elimination. Camera 0 and camera 1
are FIXED to preserve the arbitrary initial baseline (remove similarity gauge).
This is NOT metric, surveyed, georeferenced, or orthophoto-verified geometry.
Uses NumPy and OpenCV already required by SolarCheck. No SciPy/ODM dependency.
"""
from __future__ import annotations
from dataclasses import dataclass
import cv2
import numpy as np

@dataclass(frozen=True)
class RGBUnscaledBundleAdjustment:
    world_to_camera: tuple[np.ndarray, ...]
    landmark_xyz_unit_baseline: np.ndarray
    before_rmse_px: float
    after_rmse_px: float
    observation_count: int
    iterations: int
    state: str = "global_bundle_adjustment_unscaled_unverified"
    metric_scale_verified: bool = False
    roof_geometry_verified: bool = False
    orthophoto_verified: bool = False


def _projections(poses, points, camera_ids, landmark_ids, k):
    transformed = np.einsum(
        "nij,nj->ni", poses[camera_ids, :, :3], points[landmark_ids],
    ) + poses[camera_ids, :, 3]
    depth = transformed[:, 2]
    if not np.isfinite(transformed).all() or np.any(depth <= 1.e-6):
        raise ValueError("RGB BA observation behind camera or nonfinite")
    projected = np.column_stack((
        k[0] * transformed[:, 0] / depth + k[2],
        k[1] * transformed[:, 1] / depth + k[3],
    ))
    return transformed, projected


def _small_rotation(delta):
    rotation, _ = cv2.Rodrigues(np.asarray(delta, dtype=np.float64))
    return rotation


def adjust_unscaled_rgb_bundle(
    network, intrinsics, *, max_iterations=12,
    max_cameras=12, max_landmarks=400, max_observations=4000,
    huber_threshold_px=2., should_cancel=None,
):
    """Jointly refine *all selected* 3D landmarks and non-anchor camera poses.

    Requires the complete previously verified multi-camera observation bundle.
    The small all-network limit is intentional; oversized projects FAIL CLOSED
    instead of silently sampling an image subset. Scaling to the full flight
    requires a separately tested sparse/windowed optimization stage.
    """
    from mcm_solarcheck.services.rgb_global_camera_network import RGBUnscaledNetwork
    from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
    if not isinstance(network, RGBUnscaledNetwork):
        raise TypeError("existing unscaled multi-view RGB network required")
    if not isinstance(intrinsics, PinholeIntrinsics):
        raise TypeError("external calibrated RGB intrinsics required")
    if (type(max_iterations) is not int or not 1 <= max_iterations <= 40
            or type(max_cameras) is not int or not 3 <= max_cameras <= 40
            or type(max_landmarks) is not int or not 8 <= max_landmarks <= 2000
            or type(max_observations) is not int or not 24 <= max_observations <= 20000
            or type(huber_threshold_px) not in (float, int)
            or not np.isfinite(huber_threshold_px) or not .1 <= huber_threshold_px <= 10):
        raise ValueError("invalid bounded global BA resource and Huber settings")
    count = len(network.frame_ids)
    if not 3 <= count <= max_cameras or len(network.world_to_camera) != count:
        raise ValueError("global RGB camera network exceeds BA camera budget")
    points = np.asarray(network.landmark_xyz_unit_baseline, dtype=np.float64)
    cameras = np.asarray(network.world_to_camera, dtype=np.float64)
    lid = np.asarray(network.observation_landmark_indices)
    fid = np.asarray(network.observation_frame_indices)
    pixels = np.asarray(network.observation_pixels_xy, dtype=np.float64)
    k = np.asarray([intrinsics.fx, intrinsics.fy, intrinsics.cx, intrinsics.cy], dtype=np.float64)
    if (points.ndim != 2 or points.shape[1] != 3
            or not 8 <= len(points) <= max_landmarks
            or cameras.shape != (count, 3, 4)
            or fid.ndim != 1 or lid.ndim != 1 or pixels.shape != (len(fid), 2)
            or not 24 <= len(fid) <= max_observations or len(lid) != len(fid)
            or not np.issubdtype(fid.dtype, np.integer)
            or not np.issubdtype(lid.dtype, np.integer)
            or np.any(fid < 0) or np.any(fid >= count)
            or np.any(lid < 0) or np.any(lid >= len(points))
            or any(not np.isfinite(v).all() for v in (points, cameras, pixels, k))
            or np.min(k[:2]) <= 0):
        raise ValueError("invalid complete finite SfM BA observations")
    if (len(np.unique(fid)) != count
            or len(np.unique(lid)) != len(points)
            or any(np.count_nonzero(fid == j) < 8 for j in range(count))):
        raise ValueError("insufficient all-camera landmark support")
    if any(not np.allclose(c[:,:3].T@c[:,:3], np.eye(3), atol=1e-4)
           or not np.isclose(np.linalg.det(c[:,:3]), 1., atol=1e-4) for c in cameras):
        raise ValueError("invalid initial camera rotation")
    # Fix the first TWO camera poses throughout. This is explicitly an
    # arbitrary, NONMETRIC baseline; the optimizer does not establish metres.
    dof = 6 * (count - 2)
    I3 = np.eye(3)
    by_landmark = [np.flatnonzero(lid == j) for j in range(len(points))]
    def evaluate(pose_array, xyz):
        transformed, projected = _projections(pose_array, xyz, fid, lid, k)
        residual = projected - pixels
        norms = np.linalg.norm(residual, axis=1)
        h = float(huber_threshold_px)
        # Robust loss is comparable across trials and resistive to outliers.
        cost = np.sum(np.where(norms <= h, .5*norms**2, h*(norms-.5*h)))
        return transformed, residual, norms, float(cost)
    transformed, residual, norms, cost = evaluate(cameras, points)
    before = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    damping = 1.e-3
    accepted = 0
    for _ in range(max_iterations):
        if should_cancel is not None and should_cancel():
            raise RuntimeError("RGB global bundle adjustment cancelled")
        hcc = np.zeros((dof,dof))
        gcc = np.zeros(dof)
        inverse_blocks = []
        cross_blocks = []
        point_gradients = []
        # The 3D landmarks are independent conditional on the camera steps.
        for j, obs_ids in enumerate(by_landmark):
            hll = damping*I3.copy()
            gl = np.zeros(3)
            cross = np.zeros((dof,3))
            for ix in obs_ids:
                i = int(fid[ix])
                xc = transformed[ix]
                z = xc[2]
                derivative = np.array([
                    [k[0]/z, 0., -k[0]*xc[0]/z**2],
                    [0., k[1]/z, -k[1]*xc[1]/z**2],
                ])
                jl = derivative @ cameras[i,:,:3]
                r = residual[ix]
                weight = min(1., float(huber_threshold_px)/max(1e-12,norms[ix]))
                hll += weight*(jl.T@jl)
                gl += weight*(jl.T@r)
                if i >= 2:
                    skew = np.array([
                        [0.,-xc[2],xc[1]],
                        [xc[2],0.,-xc[0]],
                        [-xc[1],xc[0],0.],
                    ])
                    jc = derivative @ np.column_stack((-skew,I3))
                    sl = slice(6*(i-2),6*(i-1))
                    hcc[sl,sl] += weight*(jc.T@jc)
                    gcc[sl] += weight*(jc.T@r)
                    cross[sl] += weight*(jc.T@jl)
            inv = np.linalg.inv(hll)
            hcc -= cross@inv@cross.T
            gcc -= cross@inv@gl
            inverse_blocks.append(inv)
            cross_blocks.append(cross)
            point_gradients.append(gl)
        if dof:
            hcc += damping*np.eye(dof)
            try:
                camera_delta = np.linalg.solve(hcc,-gcc)
            except np.linalg.LinAlgError as error:
                raise ValueError("RGB global BA singular camera system") from error
        else:
            camera_delta = np.empty(0)
        candidate_points = points.copy()
        for j in range(len(points)):
            candidate_points[j] -= inverse_blocks[j]@(
                point_gradients[j]+cross_blocks[j].T@camera_delta
            )
        candidate_cameras = cameras.copy()
        for i in range(2,count):
            delta = camera_delta[6*(i-2):6*(i-1)]
            rotation = _small_rotation(delta[:3])
            candidate_cameras[i,:,:3] = rotation@cameras[i,:,:3]
            candidate_cameras[i,:,3] = rotation@cameras[i,:,3] + delta[3:]
        try:
            next_transformed,next_residual,next_norms,next_cost = evaluate(
                candidate_cameras,candidate_points,
            )
        except ValueError:
            damping *= 10.
            continue
        if next_cost < cost:
            improvement = cost-next_cost
            points,cameras = candidate_points,candidate_cameras
            transformed,residual,norms,cost = (
                next_transformed,next_residual,next_norms,next_cost
            )
            damping = max(1.e-9,damping*.5)
            accepted += 1
            if improvement < 1.e-8:
                break
        else:
            damping = min(1.e10,damping*10.)
    if accepted == 0:
        # Exact or already well-converged inputs remain usable if residuals
        # were explicitly evaluated; never claim an improvement that did not occur.
        if before > huber_threshold_px:
            raise ValueError("RGB global BA failed to improve high reprojection error")
    after = float(np.sqrt(np.mean(np.sum(residual**2,axis=1))))
    if not np.isfinite(after) or after > before + 1.e-8:
        raise ValueError("RGB global BA could not validate reprojection improvement")
    for p in cameras:
        p.setflags(write=False)
    points.setflags(write=False)
    return RGBUnscaledBundleAdjustment(
        tuple(p.copy() for p in cameras), points,
        before, after, len(fid), accepted,
    )
