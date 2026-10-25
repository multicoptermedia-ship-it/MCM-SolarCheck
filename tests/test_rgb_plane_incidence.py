"""Synthetic RGB camera-incidence checks on tilted PV module surfaces."""
from math import cos, radians, sin

import numpy as np
import pytest

from mcm_solarcheck.services.rgb_plane_incidence import inspect_rgb_plane_incidence
from mcm_solarcheck.services.module_plane_projection import CameraExtrinsicsENU, SurveyedPlane3D


def sloped(degrees):
    theta = radians(degrees)
    return SurveyedPlane3D((0, 0, 0), (sin(theta), 0, cos(theta)))


DOWN = CameraExtrinsicsENU(
    (0, 0, 10), ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.)),
)


@pytest.mark.parametrize("tilt", [0, 20, 25, 30, 45])
def test_vertical_nadir_camera_has_actual_plane_incidence_not_zero(tilt):
    result = inspect_rgb_plane_incidence(DOWN, sloped(tilt))
    assert result.plane_tilt_from_horizontal_deg == pytest.approx(tilt)
    assert result.camera_deviation_from_plane_normal_deg == pytest.approx(tilt)
    assert result.camera_angle_to_module_plane_deg == pytest.approx(90 - tilt)
    assert result.camera_faces_plane
    assert result.perpendicular_target_met is (tilt <= 20)
    assert result.reflection_review_required
    assert not result.georeferencing_verified


def test_camera_optical_axis_follows_tilted_surface_normal():
    t = radians(30)
    camera = CameraExtrinsicsENU(
        (0, 0, 10),
        ((cos(t), 0., -sin(t)), (0., -1., 0.), (-sin(t), 0., -cos(t))),
    )
    result = inspect_rgb_plane_incidence(camera, sloped(30))
    assert result.camera_deviation_from_plane_normal_deg == pytest.approx(0, abs=1e-6)
    assert result.perpendicular_target_met


def test_nadir_is_not_perpendicular_to_30_degree_modules():
    result = inspect_rgb_plane_incidence(DOWN, sloped(30))
    assert not result.perpendicular_target_met


def test_reversed_camera_does_not_pass_target():
    upward = CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.)))
    result = inspect_rgb_plane_incidence(upward, sloped(25))
    assert not result.camera_faces_plane
    assert not result.perpendicular_target_met


@pytest.mark.parametrize("bad", [float("nan"), 0, 90, -1])
def test_invalid_threshold_rejected(bad):
    with pytest.raises(ValueError, match="threshold"):
        inspect_rgb_plane_incidence(DOWN, sloped(25), maximum_deviation_deg=bad)


def test_fake_dji_gimbal_rotation_and_unverified_normal_cannot_be_accepted():
    wrong = CameraExtrinsicsENU((0, 0, 10), ((2., 0., 0.), (0., -1., 0.), (0., 0., -1.)))
    with pytest.raises(ValueError, match="rotation"):
        inspect_rgb_plane_incidence(wrong, sloped(25))
    with pytest.raises(ValueError, match="unit normal"):
        inspect_rgb_plane_incidence(DOWN, SurveyedPlane3D((0, 0, 0), (0, 0, 2)))
