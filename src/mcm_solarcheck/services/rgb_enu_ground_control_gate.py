"""Independent 3-D GCP fit and strictly HELD-OUT ENU validation for RGB SfM.

This aligns the existing UN-SCALED RGB camera/3D-landmark network to externally
provided measured 3D positions (metres). Training and hold-out landmark IDs
must be disjoint; all controls must pass an explicit absolute error gate.

Provenance strings cannot authenticate a real-world survey. The result is only
a *candidate* ENU transform, NEVER an automatically verified georeference,
orthophoto or permission to bypass the surveyed-roof control gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import numpy as np

from mcm_solarcheck.services.module_plane_projection import CameraExtrinsicsENU


@dataclass(frozen=True)
class RGBSurveyed3DControl:
    """3D SfM landmark with independent external ENU measurement in METRES."""

    control_id: str
    landmark_index: int
    point_enu_m: tuple[float, float, float]


@dataclass(frozen=True)
class RGBENUCandidate:
    scale_m_per_arbitrary_unit: float
    rotation_to_enu: np.ndarray
    origin_enu_m: np.ndarray
    camera_extrinsics_candidate: tuple[CameraExtrinsicsENU, ...]
    landmark_points_enu_candidate_m: np.ndarray
    fit_max_error_m: float
    fit_p95_error_m: float
    holdout_max_error_m: float
    holdout_p95_error_m: float
    fit_control_count: int
    held_out_control_count: int
    state: str = "survey_consistent_enu_candidate_not_authenticated"
    metric_scale_verified: bool = False
    independent_survey_authenticity_verified: bool = False
    georeferencing_verified: bool = False
    orthophoto_verified: bool = False


def _control_array(controls, landmark_count, label):
    if (type(controls) is not tuple or len(controls) < 4
            or len(controls) > 1000):
        raise ValueError(f"at least four bounded {label} 3D controls required")
    ids, indices, points = [], [], []
    for control in controls:
        if (not isinstance(control, RGBSurveyed3DControl)
                or not isinstance(control.control_id, str)
                or not control.control_id.strip()
                or type(control.landmark_index) is not int
                or not 0 <= control.landmark_index < landmark_count):
            raise ValueError(f"invalid {label} 3D control reference")
        ids.append(control.control_id)
        indices.append(control.landmark_index)
        points.append(control.point_enu_m)
    if len(set(ids)) != len(ids) or len(set(indices)) != len(indices):
        raise ValueError(f"duplicate {label} 3D control ID or landmark")
    try:
        xyz = np.asarray(points, dtype=np.float64)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError(f"finite {label} ENU coordinates required") from error
    if xyz.shape != (len(indices), 3) or not np.isfinite(xyz).all():
        raise ValueError(f"finite {label} ENU coordinates required")
    return set(ids), np.asarray(indices, dtype=np.int64), xyz


def _distributed(points, label, minimum_spread_m):
    centered = points - np.mean(points, axis=0)
    sigma = np.linalg.svd(centered, compute_uv=False)
    if (sigma[0] < minimum_spread_m / 2
            or len(sigma) < 2 or sigma[1] / sigma[0] < .05):
        raise ValueError(f"{label} controls are collinear or insufficiently distributed")


def _similarity(src, dst):
    """Proper-rotation 7-DOF Umeyama least-squares similarity, no reflection."""
    a = np.mean(src, axis=0)
    b = np.mean(dst, axis=0)
    x, y = src - a, dst - b
    cross = y.T @ x / len(src)
    u, singular, vt = np.linalg.svd(cross)
    diag = np.ones(3)
    if np.linalg.det(u @ vt) < 0:
        diag[-1] = -1
    r = u @ np.diag(diag) @ vt
    variance = np.sum(x * x) / len(src)
    if variance <= 1e-12:
        raise ValueError("degenerate 3D survey scale")
    scale = float(np.dot(singular, diag) / variance)
    if not isfinite(scale) or not 1e-6 <= scale <= 1e6:
        raise ValueError("invalid positive ENU survey scale")
    translation = b - scale * (r @ a)
    if (not np.isfinite(r).all() or not np.isfinite(translation).all()
            or np.linalg.det(r) < 0.999999):
        raise ValueError("reflected or nonfinite ENU alignment")
    return scale, r, translation


def fit_enu_candidate_from_survey(
    poses_world_to_camera_arbitrary,
    landmarks_xyz_arbitrary,
    fit_controls: tuple[RGBSurveyed3DControl, ...],
    holdout_controls: tuple[RGBSurveyed3DControl, ...],
    *,
    fit_survey_provenance: str,
    holdout_survey_provenance: str,
    allowed_max_error_m: float,
    minimum_spread_m: float = .5,
    should_cancel=None,
) -> RGBENUCandidate:
    """Fit using training GCPs; NEVER use hold-outs in optimization.

    Rejects degenerate layouts, duplicate IDs, physical mirror reflection,
    incorrect scale and even one excessive GCP/holdout residual. The
    caller must still externally authenticate surveys/calibration and
    independently verify the actual surveyed roof for any metric product.
    """
    if should_cancel is not None and should_cancel():
        raise RuntimeError("RGB ENU control survey cancelled")
    for name, provenance in (("fitting", fit_survey_provenance),
                             ("hold-out", holdout_survey_provenance)):
        if not isinstance(provenance, str) or not provenance.strip():
            raise ValueError(f"{name} external survey provenance required")
    if (type(allowed_max_error_m) not in (int,float)
            or not isfinite(allowed_max_error_m)
            or not 0 < allowed_max_error_m <= 2
            or type(minimum_spread_m) not in (int,float)
            or not isfinite(minimum_spread_m)
            or not .1 <= minimum_spread_m <= 100):
        raise ValueError("finite bounded metric control tolerance and spread required")
    pose = np.asarray(poses_world_to_camera_arbitrary, dtype=np.float64)
    pts = np.asarray(landmarks_xyz_arbitrary, dtype=np.float64)
    if (pose.ndim != 3 or pose.shape[1:] != (3,4)
            or not 3 <= len(pose) <= 1000
            or pts.ndim != 2 or pts.shape[1] != 3
            or not 8 <= len(pts) <= 200000
            or not np.isfinite(pose).all() or not np.isfinite(pts).all()):
        raise ValueError("finite complete unscaled camera/landmark network required")
    for p in pose:
        r = p[:,:3]
        if (not np.allclose(r.T @ r,np.eye(3),atol=1e-5)
                or not np.isclose(np.linalg.det(r),1.,atol=1e-5)):
            raise ValueError("invalid SfM world-to-camera rotation")
    fit_ids, fit_idx, fitting = _control_array(fit_controls,len(pts),"fitting")
    hold_ids, hold_idx, held = _control_array(holdout_controls,len(pts),"held-out")
    if fit_ids & hold_ids or set(fit_idx.tolist()) & set(hold_idx.tolist()):
        raise ValueError("fitting GCPs and held-out controls must be independent")
    _distributed(fitting,"fitting",float(minimum_spread_m))
    _distributed(held,"held-out",float(minimum_spread_m))
    _distributed(pts[fit_idx],"SfM fitting",1e-5)
    scale,r,t = _similarity(pts[fit_idx],fitting)
    predicted_fit = scale * (pts[fit_idx] @ r.T) + t
    predicted_hold = scale * (pts[hold_idx] @ r.T) + t
    fit_err = np.linalg.norm(predicted_fit-fitting,axis=1)
    hold_err = np.linalg.norm(predicted_hold-held,axis=1)
    if (not np.isfinite(fit_err).all() or not np.isfinite(hold_err).all()
            or np.max(fit_err)>allowed_max_error_m
            or np.max(hold_err)>allowed_max_error_m):
        raise ValueError("independent ENU GCP or hold-out residual exceeds metric tolerance")
    if should_cancel is not None and should_cancel():
        raise RuntimeError("RGB ENU control survey cancelled")
    extrinsics=[]
    for camera in pose:
        q, offset=camera[:,:3],camera[:,3]
        center_unscaled=-q.T @ offset
        center_enu = scale * r @ center_unscaled + t
        camera_to_enu = r @ q.T
        extrinsics.append(CameraExtrinsicsENU(
            tuple(float(v) for v in center_enu),
            tuple(tuple(float(v) for v in row) for row in camera_to_enu),
        ))
    mapped=scale * (pts @ r.T) + t
    for array in (r,t,mapped):
        array.setflags(write=False)
    return RGBENUCandidate(
        scale,r,t,tuple(extrinsics),mapped,
        float(np.max(fit_err)),float(np.percentile(fit_err,95)),
        float(np.max(hold_err)),float(np.percentile(hold_err,95)),
        len(fit_idx),len(hold_idx),
    )
