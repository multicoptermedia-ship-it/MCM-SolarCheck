"""Synthetic whole-flight RTK-to-existing-windowed-BA bridge; no private GPS."""
from dataclasses import replace
from pathlib import Path
import json

import numpy as np
import pytest

from mcm_solarcheck.domain.models import Pose, Position, RTKQuality
from mcm_solarcheck.services.rgb_flight_zip_series import (
    PrivateRGBFlightFrame, PrivateRGBFlightSeries,
)
from mcm_solarcheck.services.rgb_global_camera_network import RGBUnscaledNetwork
from mcm_solarcheck.services.rgb_windowed_bundle_adjustment import RGBWindowedBAResult
from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services import rgb_rtk_camera_priors as service


def _flight(count=160):
    """Known ENU metric camera path, converted to nearby synthetic DJI GNSS."""
    i = np.arange(count, dtype=float)
    centers = np.column_stack((
        .28 * i, 2 * np.sin(i / 12), .4 * np.cos(i / 21),
    ))
    angle = np.deg2rad(24.)
    rotation = np.array([
        [np.cos(angle), -np.sin(angle), 0.],
        [np.sin(angle), np.cos(angle), 0.],
        [0., 0., 1.],
    ])
    true_m = 1.7 * centers @ rotation.T + np.array((12., -8., 1.5))
    lat0, lon0, height = 50., 7., 100.
    # millimetre-level local-coordinate accuracy at the synthetic <100m extent
    frames = []
    poses = []
    for n, (center, enu) in enumerate(zip(centers, true_m), 1):
        lat = lat0 + enu[1] / 111230.
        lon = lon0 + enu[0] / (111320. * np.cos(np.deg2rad(lat0)))
        pos = Position(lat, lon, height + enu[2])
        frames.append(PrivateRGBFlightFrame(
            Path("private-only.zip"),
            f"private/DJI_20260825120000_{n:04d}_V.JPG",
            f"V-{n:04d}", "20260825120000", 4000, 3000,
            pos, Pose(2., -90., 0.), Pose(3., 0., 0.),
            RTKQuality("50", .012, .013, .025, altitude_type="RtkAlt"),
            ("DewarpData",), 12345,
        ))
        poses.append(np.column_stack((np.eye(3), -center)))
    points = np.column_stack((
        np.arange(16, dtype=float) / 10,
        np.arange(16, dtype=float) / 20,
        np.arange(16, dtype=float) / 30 + 7,
    ))
    frame_ids = tuple(f.frame_id for f in frames)
    network = RGBUnscaledNetwork(
        frame_ids, tuple(poses), len(points), len(points), count - 1, 0., 0.,
        landmark_xyz_unit_baseline=points,
        observation_frame_indices=np.zeros(0, dtype=np.int32),
        observation_landmark_indices=np.zeros(0, dtype=np.int32),
        observation_pixels_xy=np.zeros((0, 2)),
    )
    result = RGBWindowedBAResult(
        tuple(poses), points, 1.5, 0.7, 2., 1., count, len(points),
        16 * count, max(1, count // 4), 6,
    )
    return PrivateRGBFlightSeries(tuple(frames), 6, 0), network, result


def test_synthetic_160_rtk_camera_priors_anchor_existing_window_ba_without_survey_claim():
    series, network, windowed = _flight()
    priors = service.build_private_rtk_camera_priors(series, network.frame_ids)
    assert priors.camera_enu_m.shape == (160, 3)
    assert priors.gimbal_ypr_deg.shape == (160, 3)
    assert priors.flight_ypr_deg.shape == (160, 3)
    assert priors.sigma_enu_m[0, 0] >= .1
    assert priors.sigma_enu_m[0, 2] >= .2
    assert priors.altitude_type == "RtkAlt"
    assert not priors.altitude_datum_verified
    assert not priors.attitude_convention_verified
    answer = service.anchor_windowed_rgb_network_to_rtk(network, windowed, priors)
    assert answer.camera_count == 160
    assert answer.training_camera_count == 128
    assert answer.withheld_camera_count == 32
    assert abs(answer.scale_m_per_sfm_unit - 1.7) < .002
    assert answer.withheld_p95_m < .05
    assert answer.fit_p95_m < .05
    assert answer.reprojection_rmse_px_after_windowed_ba == 0.7
    assert len(answer.cameras_enu_candidate) == 160
    assert answer.landmarks_enu_candidate_private_m.shape == (16, 3)
    assert not answer.gnss_joint_bundle_adjustment_completed
    assert not answer.independent_georeference_verified
    assert not answer.roof_geometry_verified
    assert not answer.orthophoto_verified
    report = json.dumps(answer.privacy_safe_summary())
    assert "50.0" not in report
    assert "private" not in report
    assert "V-0001" not in report
    assert "RtkAlt" not in report
    assert "orthophoto_verified" in report
    assert not priors.camera_enu_m.flags.writeable


def test_mismatched_missing_and_duplicate_flight_camera_priors_fail_closed():
    series, network, windowed = _flight(16)
    with pytest.raises(ValueError, match="match|complete"):
        service.build_private_rtk_camera_priors(
            series, network.frame_ids[:-1] + ("WRONG",),
        )
    with pytest.raises(ValueError, match="complete"):
        service.build_private_rtk_camera_priors(
            series, network.frame_ids[:-1],
        )
    with pytest.raises(ValueError, match="unique"):
        service.build_private_rtk_camera_priors(
            series, network.frame_ids[:-1] + (network.frame_ids[0],),
        )
    broken = replace(series.frames[0], rtk=RTKQuality("50", altitude_type="RtkAlt"))
    with pytest.raises(ValueError, match="complete"):
        service.build_private_rtk_camera_priors(
            replace(series, frames=(broken,) + series.frames[1:]),
            network.frame_ids,
        )
    priors = service.build_private_rtk_camera_priors(series, network.frame_ids)
    with pytest.raises(RuntimeError, match="cancelled"):
        service.anchor_windowed_rgb_network_to_rtk(
            network, windowed, priors, should_cancel=lambda: True,
        )


def test_held_back_rtk_outlier_cannot_get_silently_accepted():
    series, network, windowed = _flight(20)
    modified = list(series.frames)
    # Camera index 4 is withheld by deterministic stride.
    frame = modified[4]
    modified[4] = replace(
        frame, position=replace(frame.position,
                                longitude=frame.position.longitude + .0002),
    )
    priors = service.build_private_rtk_camera_priors(
        replace(series, frames=tuple(modified)), network.frame_ids,
    )
    with pytest.raises(ValueError, match="withheld RTK"):
        service.anchor_windowed_rgb_network_to_rtk(
            network, windowed, priors, max_withheld_error_m=1.,
        )


def test_orchestration_reuses_existing_windowed_ba_without_making_up_geometry(monkeypatch):
    series, network, expected = _flight(16)
    calls = []
    def run_existing(actual_network, actual_k, **options):
        calls.append((actual_network, actual_k, options))
        return expected
    monkeypatch.setattr(
        service, "adjust_windowed_unscaled_rgb_network", run_existing,
    )
    k = PinholeIntrinsics(700., 700., 400., 300.)
    answer = service.adjust_and_anchor_private_rgb_flight(
        network, k, series, windowed_ba_options={"max_iterations": 2},
    )
    assert answer.camera_count == 16
    assert calls[0][0] is network
    assert calls[0][1] is k
    assert calls[0][2]["max_iterations"] == 2
    assert answer.state.endswith("candidate_unverified")
    assert not answer.gnss_joint_bundle_adjustment_completed
