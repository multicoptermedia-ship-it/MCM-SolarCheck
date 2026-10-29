"""Private metric-candidate RTK-constrained windowed RGB bundle adjustment.

Uses the existing SfM tracks, prior windowed BA, robust GNSS similarity,
and the Schur/window optimizer with fitted ENU camera-position priors.
Independent RTK hold-outs are not independent survey/GCP measurements.
No customer GPS, images, paths or numerical coordinates are published.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import numpy as np

from mcm_solarcheck.services.rgb_global_camera_network import RGBUnscaledNetwork
from mcm_solarcheck.services.rgb_windowed_bundle_adjustment import (
    RGBWindowedBAResult, adjust_windowed_unscaled_rgb_network,
)
from mcm_solarcheck.services.rgb_rtk_camera_priors import (
    PrivateRGBRTKPriors, anchor_windowed_rgb_network_to_rtk,
)
from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_per_camera_reprojection_gate import (
    RGBPerCameraReprojectionAudit, audit_rgb_per_camera_reprojection,
)


@dataclass(frozen=True)
class PrivateRGBRTKWindowedBA:
    """In-memory ENU candidate only: not a metric product or roof orthophoto."""

    frame_ids: tuple[str, ...]
    world_enu_to_camera_private: tuple[np.ndarray, ...]
    landmarks_enu_private_m: np.ndarray
    before_reprojection_rmse_px: float
    after_reprojection_rmse_px: float
    before_rtk_holdout_p95_m: float
    after_rtk_holdout_p95_m: float
    after_rtk_holdout_max_m: float
    fitted_rtk_camera_count: int
    withheld_rtk_camera_count: int
    total_cameras: int
    completed_windows: int
    joint_objective_before: float
    joint_objective_after: float
    windows_with_updates: int = 0
    windows_without_improvement: int = 0
    state: str = "rtk_regularized_multiview_windowed_ba_unverified"
    rtk_prior_windowed_ba_completed: bool = True
    full_global_joint_ba_completed: bool = False
    independent_survey_verified: bool = False
    roof_geometry_verified: bool = False
    orthophoto_verified: bool = False
    camera_reprojection_audit: RGBPerCameraReprojectionAudit | None = None

    def privacy_safe_summary(self):
        return {
            "schema": "mcm.rgb_rtk_windowed_ba.v1",
            "status": self.state,
            "camera_count": self.total_cameras,
            "windows": self.completed_windows,
            "windows_with_updates": self.windows_with_updates,
            "windows_without_improvement": self.windows_without_improvement,
            "gnss_fit_camera_count": self.fitted_rtk_camera_count,
            "gnss_withheld_camera_count": self.withheld_rtk_camera_count,
            "before_reprojection_rmse_px": self.before_reprojection_rmse_px,
            "after_reprojection_rmse_px": self.after_reprojection_rmse_px,
            "per_camera_reprojection": (
                self.camera_reprojection_audit.privacy_safe_summary()
                if self.camera_reprojection_audit is not None else None
            ),
            "before_rtk_holdout_p95_m": self.before_rtk_holdout_p95_m,
            "after_rtk_holdout_p95_m": self.after_rtk_holdout_p95_m,
            "after_rtk_holdout_max_m": self.after_rtk_holdout_max_m,
            "joint_objective_before": self.joint_objective_before,
            "joint_objective_after": self.joint_objective_after,
            "rtk_prior_windowed_ba_completed": True,
            "full_global_joint_ba_completed": False,
            "independent_survey_verified": False,
            "roof_geometry_verified": False,
            "orthophoto_verified": False,
        }


def adjust_rgb_windowed_bundle_with_private_rtk(
    network: RGBUnscaledNetwork,
    unscaled_windowed: RGBWindowedBAResult,
    priors: PrivateRGBRTKPriors,
    intrinsics: PinholeIntrinsics,
    *,
    max_rtk_holdout_m: float = 2.,
    windowed_options: dict | None = None,
    should_cancel=None,
) -> PrivateRGBRTKWindowedBA:
    """One complete existing SfM flight -> aligned ENU -> robust GNSS window BA.

    The 20%-withheld RTK cameras NEVER contribute to similarity fitting OR
    optimization priors; they still participate in the common pixel tracks.
    Changes to camera zero and one are allowed, unlike unscaled legacy BA.
    """
    if should_cancel is not None and should_cancel():
        raise RuntimeError("RTK-weighted RGB flight cancelled")
    if (not isinstance(network, RGBUnscaledNetwork)
            or not isinstance(unscaled_windowed, RGBWindowedBAResult)
            or not isinstance(priors, PrivateRGBRTKPriors)
            or not isinstance(intrinsics, PinholeIntrinsics)):
        raise TypeError("existing full SfM/windowed BA and DJI RTK priors required")
    n = len(network.frame_ids)
    if (n < 12 or n > 1000 or priors.frame_ids != network.frame_ids
            or unscaled_windowed.camera_count != n
            or len(unscaled_windowed.world_to_camera) != n):
        raise ValueError("full RGB flight and matched RTK camera identities required")
    aligned = anchor_windowed_rgb_network_to_rtk(
        network, unscaled_windowed, priors,
        max_withheld_error_m=max_rtk_holdout_m,
        should_cancel=should_cancel,
    )
    if not 0.05 <= max_rtk_holdout_m <= 20:
        raise ValueError("explicit RTK consistency tolerance required")
    scale, rotation, origin = (
        aligned.scale_m_per_sfm_unit, aligned.rotation_sfm_to_enu,
        aligned.translation_enu_private_m,
    )
    # X_ENU = scale * rotation * X_SfM + origin. The equivalent
    # world-ENU->camera pose must preserve EVERY original reprojection:
    # R_ENU = R_SfM * rotation.T, t_ENU = scale*t_SfM - R_ENU*origin.
    poses = []
    for pose in unscaled_windowed.world_to_camera:
        r = pose[:, :3] @ rotation.T
        t = scale * pose[:, 3] - r @ origin
        poses.append(np.column_stack((r, t)))
    metric_candidate = replace(
        network,
        world_to_camera=tuple(poses),
        landmark_xyz_unit_baseline=aligned.landmarks_enu_candidate_private_m,
    )
    fit = np.arange(n) % 5 != 4
    # No GNSS target is supplied for a held-out camera to the BA.
    options = dict(windowed_options or {})
    restricted = {
        "rtk_camera_centers_m", "rtk_camera_sigmas_m", "rtk_fit_mask",
        "gnss_huber_sigma", "should_cancel",
    }
    if restricted & options.keys():
        raise ValueError("RTK uncertainty, fit/holdout mask and cancellation are internal")
    fitted = adjust_windowed_unscaled_rgb_network(
        metric_candidate, intrinsics,
        rtk_camera_centers_m=priors.camera_enu_m,
        rtk_camera_sigmas_m=priors.sigma_enu_m,
        rtk_fit_mask=fit,
        gnss_huber_sigma=3.,
        should_cancel=should_cancel,
        **options,
    )
    if not fitted.rtk_camera_priors_optimized:
        raise ValueError("joint RTK-prior camera BA was not executed")
    out_poses = np.asarray(fitted.world_to_camera)
    center = -np.einsum("nji,nj->ni", out_poses[:, :, :3], out_poses[:, :, 3])
    error = np.linalg.norm(center[~fit] - priors.camera_enu_m[~fit], axis=1)
    if (not np.isfinite(error).all()
            or float(error.max()) > max_rtk_holdout_m
            or fitted.weighted_objective_before is None
            or fitted.weighted_objective_after is None
            or fitted.weighted_objective_after > fitted.weighted_objective_before+1e-8):
        raise ValueError("independent RTK holdout consistency or joint BA objective failed")
    result_poses = tuple(np.array(p,copy=True) for p in fitted.world_to_camera)
    xyz = np.array(fitted.landmark_xyz_unit_baseline,copy=True)
    for array in (*result_poses,xyz):
        array.setflags(write=False)
    pixel_audit = audit_rgb_per_camera_reprojection(
        result_poses, xyz,
        network.observation_frame_indices,
        network.observation_landmark_indices,
        network.observation_pixels_xy,
        intrinsics, should_cancel=should_cancel,
    )
    return PrivateRGBRTKWindowedBA(
        network.frame_ids, result_poses, xyz, fitted.before_rmse_px,
        fitted.after_rmse_px, aligned.withheld_p95_m,
        float(np.percentile(error,95)), float(error.max()),
        int(np.sum(fit)), int(np.sum(~fit)), n, fitted.completed_windows,
        float(fitted.weighted_objective_before),
        float(fitted.weighted_objective_after),
        fitted.rtk_windows_with_updates,
        fitted.rtk_windows_without_improvement,
        state=("rtk_regularized_windows_with_rejections_unverified"
               if fitted.rtk_windows_without_improvement else
               "rtk_regularized_multiview_windowed_ba_unverified"),
        camera_reprojection_audit=pixel_audit,
    )
