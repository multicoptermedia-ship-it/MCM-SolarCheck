"""Private DJI RTK -> local ENU camera priors for the existing multi-view SfM/BA.

This is the first metric *candidate* bridge after unscaled windowed BA, NOT
GNSS-constrained bundle adjustment, roof reconstruction or an orthophoto.
All absolute positions stay in memory; public reports must not serialize these
objects. Only NumPy and the existing SolarCheck code are used.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
import numpy as np

from mcm_solarcheck.services.rgb_flight_zip_series import PrivateRGBFlightSeries
from mcm_solarcheck.services.rgb_global_camera_network import RGBUnscaledNetwork
from mcm_solarcheck.services.rgb_windowed_bundle_adjustment import (
    RGBWindowedBAResult, adjust_windowed_unscaled_rgb_network,
)
from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics,
)

_WGS84_A = 6378137.0
_WGS84_E2 = 6.6943799901413165e-3


@dataclass(frozen=True)
class PrivateRGBRTKPriors:
    """Private local ENU metres, uncertain 1-sigma floors, original attitude."""
    frame_ids: tuple[str, ...]
    reference_geodetic_private: tuple[float, float, float]
    camera_enu_m: np.ndarray
    sigma_enu_m: np.ndarray
    gimbal_ypr_deg: np.ndarray
    flight_ypr_deg: np.ndarray
    rtk_statuses: tuple[str, ...]
    altitude_type: str
    altitude_datum_verified: bool = False
    attitude_convention_verified: bool = False


@dataclass(frozen=True)
class RGBRTKENUAlignment:
    """RTK-relative georeferencing candidate; no absolute/survey quality claim."""
    scale_m_per_sfm_unit: float
    rotation_sfm_to_enu: np.ndarray
    translation_enu_private_m: np.ndarray
    cameras_enu_candidate: tuple[CameraExtrinsicsENU, ...]
    landmarks_enu_candidate_private_m: np.ndarray
    fit_p95_m: float
    fit_max_m: float
    withheld_p95_m: float
    withheld_max_m: float
    training_camera_count: int
    withheld_camera_count: int
    camera_count: int
    reprojection_rmse_px_after_windowed_ba: float
    state: str = "rtk_anchored_rgb_windowed_ba_candidate_unverified"
    gnss_joint_bundle_adjustment_completed: bool = False
    independent_georeference_verified: bool = False
    roof_geometry_verified: bool = False
    orthophoto_verified: bool = False

    def privacy_safe_summary(self) -> dict:
        """No absolute/relative GPS, ENU points, source names or frame IDs."""
        return {
            "schema": "mcm.rgb_rtk_camera_anchor.v1",
            "status": self.state,
            "cameras": self.camera_count,
            "rtk_fit_cameras": self.training_camera_count,
            "rtk_withheld_cameras": self.withheld_camera_count,
            "fit_p95_m": self.fit_p95_m,
            "fit_max_m": self.fit_max_m,
            "rtk_withheld_p95_m": self.withheld_p95_m,
            "rtk_withheld_max_m": self.withheld_max_m,
            "reprojection_rmse_px": self.reprojection_rmse_px_after_windowed_ba,
            "gnss_joint_bundle_adjustment_completed": False,
            "independent_georeference_verified": False,
            "roof_geometry_verified": False,
            "orthophoto_verified": False,
        }


def _ecef(latitude, longitude, altitude):
    lat, lon = radians(latitude), radians(longitude)
    s, c = sin(lat), cos(lat)
    n = _WGS84_A / np.sqrt(1 - _WGS84_E2 * s * s)
    return np.array(((n + altitude) * c * cos(lon),
                     (n + altitude) * c * sin(lon),
                     (n * (1 - _WGS84_E2) + altitude) * s), dtype=np.float64)


def build_private_rtk_camera_priors(
    series: PrivateRGBFlightSeries,
    frame_ids: tuple[str, ...],
    *,
    horizontal_sigma_floor_m: float = .10,
    vertical_sigma_floor_m: float = .20,
    should_cancel=None,
) -> PrivateRGBRTKPriors:
    """Require a one-to-one *entire* DJI series and network frame mapping.

    ECEF/ENU treats the reported heights as one common ellipsoidal convention
    only for RELATIVE local alignment. DJI RtkAlt vertical datum and RTK fix
    status are not authenticated; do not use these priors as survey truth.
    """
    if not isinstance(series, PrivateRGBFlightSeries):
        raise TypeError("private DJI ZIP series required")
    if (type(frame_ids) is not tuple or len(frame_ids) < 12
            or len(frame_ids) > 1000
            or any(not isinstance(x, str) or not x for x in frame_ids)
            or len(set(frame_ids)) != len(frame_ids)
            or len(series.frames) != len(frame_ids)):
        raise ValueError("complete unique 12+ camera RGB flight required")
    if (not 0 < horizontal_sigma_floor_m <= 10
            or not 0 < vertical_sigma_floor_m <= 20
            or not np.isfinite([horizontal_sigma_floor_m, vertical_sigma_floor_m]).all()):
        raise ValueError("bounded finite RTK uncertainty floors required")
    lookup = {x.frame_id: x for x in series.frames}
    if len(lookup) != len(frame_ids) or set(lookup) != set(frame_ids):
        raise ValueError("RTK image identities must exactly match complete SfM flight")
    positions, sigmas, gimbals, flights, statuses, datums = [], [], [], [], [], []
    for fid in frame_ids:
        if should_cancel is not None and should_cancel():
            raise RuntimeError("private RGB RTK anchoring cancelled")
        frame = lookup[fid]
        p, rtk = frame.position, frame.rtk
        if p is None or p.altitude_m is None or any(x is None for x in (
            rtk.status, rtk.altitude_type, rtk.std_lat_m,
            rtk.std_lon_m, rtk.std_height_m,
            frame.camera_pose.yaw_deg, frame.camera_pose.pitch_deg,
            frame.camera_pose.roll_deg, frame.flight_pose.yaw_deg,
            frame.flight_pose.pitch_deg, frame.flight_pose.roll_deg,
        )):
            raise ValueError("complete DJI RTK/GNSS/height/attitude priors required")
        xyz = (p.latitude, p.longitude, p.altitude_m)
        stdev = (rtk.std_lon_m, rtk.std_lat_m, rtk.std_height_m)
        gimbal = (frame.camera_pose.yaw_deg, frame.camera_pose.pitch_deg,
                  frame.camera_pose.roll_deg)
        flight = (frame.flight_pose.yaw_deg, frame.flight_pose.pitch_deg,
                  frame.flight_pose.roll_deg)
        if (not np.isfinite((*xyz, *stdev, *gimbal, *flight)).all()
                or not -90 <= xyz[0] <= 90 or not -180 <= xyz[1] <= 180
                or any(x < 0 or x > 20 for x in stdev)
                or any(abs(x) > 360 for x in (*gimbal, *flight))
                or not rtk.status.strip() or not rtk.altitude_type.strip()):
            raise ValueError("invalid DJI RTK/GNSS/attitude prior")
        positions.append(xyz)
        sigmas.append((max(stdev[0], horizontal_sigma_floor_m),
                       max(stdev[1], horizontal_sigma_floor_m),
                       max(stdev[2], vertical_sigma_floor_m)))
        gimbals.append(gimbal)
        flights.append(flight)
        statuses.append(rtk.status)
        datums.append(rtk.altitude_type)
    if len(set(datums)) != 1:
        raise ValueError("mixed DJI altitude references cannot share ENU")
    ref_lat, ref_lon, ref_h = positions[0]
    lat, lon = radians(ref_lat), radians(ref_lon)
    origin = _ecef(ref_lat, ref_lon, ref_h)
    east = np.array((-sin(lon), cos(lon), 0.))
    north = np.array((-sin(lat) * cos(lon), -sin(lat) * sin(lon), cos(lat)))
    up = np.array((cos(lat) * cos(lon), cos(lat) * sin(lon), sin(lat)))
    basis = np.stack((east, north, up))
    enu = np.array([basis @ (_ecef(*xyz) - origin) for xyz in positions])
    if not np.isfinite(enu).all():
        raise ValueError("nonfinite local ENU camera positions")
    sigma = np.asarray(sigmas, dtype=np.float64)
    gimbal = np.asarray(gimbals, dtype=np.float64)
    flight = np.asarray(flights, dtype=np.float64)
    for array in (enu, sigma, gimbal, flight):
        array.setflags(write=False)
    return PrivateRGBRTKPriors(
        frame_ids, (ref_lat, ref_lon, ref_h), enu, sigma,
        gimbal, flight, tuple(statuses), datums[0],
    )


def _weighted_similarity(src, dst, weights):
    """Weighted proper-rotation Umeyama with positive scale; no reflections."""
    w = weights / np.sum(weights)
    p = w @ src
    q = w @ dst
    a, b = src - p, dst - q
    cross = (b * w[:, None]).T @ a
    u, singular, vt = np.linalg.svd(cross)
    correction = np.eye(3)
    correction[-1, -1] = np.sign(np.linalg.det(u @ vt))
    rotation = u @ correction @ vt
    variance = float(np.sum(w[:, None] * a * a))
    if variance < 1e-12:
        raise ValueError("degenerate SfM camera centers")
    scale = float(np.sum(singular * np.diag(correction)) / variance)
    translation = q - scale * (rotation @ p)
    if (not np.isfinite(scale) or not 1e-6 <= scale <= 1e6
            or not np.isfinite(rotation).all()
            or not np.isfinite(translation).all()
            or np.linalg.det(rotation) < .99999):
        raise ValueError("invalid RTK-to-SfM camera similarity")
    return scale, rotation, translation


def anchor_windowed_rgb_network_to_rtk(
    network: RGBUnscaledNetwork,
    result: RGBWindowedBAResult,
    priors: PrivateRGBRTKPriors,
    *,
    max_withheld_error_m: float = 2.0,
    should_cancel=None,
) -> RGBRTKENUAlignment:
    """Align windowed SfM to RTK, with withheld *RTK* frames for diagnostics.

    Withheld RTK is NOT independent survey control. This does not reoptimize
    pixels/landmarks or apply DJI yaw/pitch/roll (its camera-axis convention
    still needs validation). The subsequent step is joint GNSS-prior BA.
    """
    if should_cancel is not None and should_cancel():
        raise RuntimeError("private RGB RTK anchoring cancelled")
    if (not isinstance(network, RGBUnscaledNetwork)
            or not isinstance(result, RGBWindowedBAResult)
            or not isinstance(priors, PrivateRGBRTKPriors)):
        raise TypeError("whole-flight network, windowed BA and private RTK priors required")
    count = len(network.frame_ids)
    if (count < 12 or count > 1000 or tuple(priors.frame_ids) != network.frame_ids
            or result.camera_count != count
            or len(result.world_to_camera) != count
            or result.landmark_count < 8
            or not isinstance(priors.altitude_type, str)
            or not priors.altitude_type):
        raise ValueError("complete matched RGB/RTK/windowed camera bundle required")
    if (not np.isfinite(max_withheld_error_m)
            or not .05 <= max_withheld_error_m <= 20):
        raise ValueError("explicit bounded RTK consistency tolerance required")
    poses = np.asarray(result.world_to_camera, dtype=np.float64)
    landmarks = np.asarray(result.landmark_xyz_unit_baseline, dtype=np.float64)
    gnss = np.asarray(priors.camera_enu_m, dtype=np.float64)
    sigma = np.asarray(priors.sigma_enu_m, dtype=np.float64)
    if (poses.shape != (count, 3, 4)
            or landmarks.shape != (result.landmark_count, 3)
            or gnss.shape != (count, 3) or sigma.shape != (count, 3)
            or not all(np.isfinite(x).all() for x in (poses, landmarks, gnss, sigma))
            or np.any(sigma <= 0)):
        raise ValueError("invalid finite whole-flight RGB/RTK geometry")
    if any(not np.allclose(p[:, :3].T @ p[:, :3], np.eye(3), atol=1e-4)
           or not np.isclose(np.linalg.det(p[:, :3]), 1., atol=1e-4)
           for p in poses):
        raise ValueError("invalid SfM camera rotations")
    centers = -np.einsum("nji,nj->ni", poses[:, :, :3], poses[:, :, 3])
    # Every fifth frame is withheld from the similarity fit, including edges
    # across the original flight. This tests interpolation, NOT survey truth.
    held = np.arange(count) % 5 == 4
    train = ~held
    if np.count_nonzero(held) < 2 or np.count_nonzero(train) < 8:
        raise ValueError("insufficient RTK fitting and withheld cameras")
    xy = gnss[train] - gnss[train].mean(axis=0)
    singular = np.linalg.svd(xy, compute_uv=False)
    if (singular[0] < 1 or singular[1] < .03 * singular[0]
            or np.linalg.svd(centers[train] - centers[train].mean(axis=0),
                             compute_uv=False)[1] < 1e-5):
        raise ValueError("RTK/SfM flight camera geometry insufficiently distributed")
    base = 1.0 / np.mean(sigma[train] ** 2, axis=1)
    weights = base.copy()
    for _ in range(8):
        if should_cancel is not None and should_cancel():
            raise RuntimeError("private RGB RTK anchoring cancelled")
        scale, rotation, translation = _weighted_similarity(
            centers[train], gnss[train], weights,
        )
        diff = scale * (centers[train] @ rotation.T) + translation - gnss[train]
        norm = np.linalg.norm(diff / sigma[train], axis=1)
        robust = np.minimum(1.0, 3.0 / np.maximum(norm, 1e-9))
        weights = base * robust
    scale, rotation, translation = _weighted_similarity(
        centers[train], gnss[train], weights,
    )
    predicted = scale * (centers @ rotation.T) + translation
    residual = np.linalg.norm(predicted - gnss, axis=1)
    if (not np.isfinite(residual).all()
            or float(residual[held].max()) > max_withheld_error_m):
        raise ValueError("withheld RTK camera residual exceeds stated tolerance")
    extrinsics = tuple(
        CameraExtrinsicsENU(
            tuple(float(v) for v in predicted[i]),
            tuple(tuple(float(v) for v in row)
                  for row in (rotation @ poses[i, :, :3].T)),
        )
        for i in range(count)
    )
    transformed_landmarks = scale * (landmarks @ rotation.T) + translation
    for array in (rotation, translation, transformed_landmarks):
        array.setflags(write=False)
    return RGBRTKENUAlignment(
        scale, rotation, translation, extrinsics, transformed_landmarks,
        float(np.percentile(residual[train], 95)),
        float(np.max(residual[train])),
        float(np.percentile(residual[held], 95)),
        float(np.max(residual[held])),
        int(np.sum(train)), int(np.sum(held)), count,
        float(result.after_rmse_px),
    )


def adjust_and_anchor_private_rgb_flight(
    network: RGBUnscaledNetwork,
    intrinsics: PinholeIntrinsics,
    series: PrivateRGBFlightSeries,
    *,
    windowed_ba_options: dict | None = None,
    max_withheld_error_m: float = 2.0,
    should_cancel=None,
) -> RGBRTKENUAlignment:
    """One in-memory handoff: existing complete SfM -> window BA -> RTK ENU.

    Does not claim a finished GNSS-weighted BA or orthorectified roof.
    """
    priors = build_private_rtk_camera_priors(
        series, network.frame_ids, should_cancel=should_cancel,
    )
    options = dict(windowed_ba_options or {})
    if "should_cancel" in options:
        raise ValueError("single shared cancellation callback required")
    windowed = adjust_windowed_unscaled_rgb_network(
        network, intrinsics, should_cancel=should_cancel, **options,
    )
    return anchor_windowed_rgb_network_to_rtk(
        network, windowed, priors,
        max_withheld_error_m=max_withheld_error_m,
        should_cancel=should_cancel,
    )
