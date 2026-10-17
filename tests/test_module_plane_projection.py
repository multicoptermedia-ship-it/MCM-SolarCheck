"""Synthetic calibrated ENU camera and inclined PV plane intersections."""
import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D,
    project_pixels_to_surveyed_plane,
)


K = PinholeIntrinsics(100, 100, 0, 0)
# Camera x points east, y points south, z points down in ENU.
DOWN = CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.)))


def test_nadir_ray_intersects_flat_plane_at_origin():
    xyz = project_pixels_to_surveyed_plane(np.array([[0., 0.], [10., 0.]]), K, DOWN, SurveyedPlane3D((0, 0, 0), (0, 0, 1)))
    np.testing.assert_allclose(xyz, [[0, 0, 0], [1, 0, 0]], atol=1e-10)


def test_tilted_plane_changes_pixel_to_world_mapping():
    normal = np.array([-1., 0., 1.]) / np.sqrt(2.)
    plane = SurveyedPlane3D((0, 0, 0), tuple(normal))
    xyz = project_pixels_to_surveyed_plane(np.array([[0., 0.], [10., 0.]]), K, DOWN, plane)
    np.testing.assert_allclose(xyz[0], [0, 0, 0], atol=1e-10)
    assert 0.0 < xyz[1, 0] < 1.0
    np.testing.assert_allclose(xyz[:, 2], xyz[:, 0], atol=1e-10)


@pytest.mark.parametrize("pixels,extrinsics,plane", [
    ([[0., 0.]], CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))), SurveyedPlane3D((0, 0, 0), (0, 0, 1))),
    ([[0., 0.]], DOWN, SurveyedPlane3D((0, 0, 0), (1, 0, 0))),
    ([[float("nan"), 0.]], DOWN, SurveyedPlane3D((0, 0, 0), (0, 0, 1))),
])
def test_reject_behind_parallel_and_nonfinite_rays(pixels, extrinsics, plane):
    with pytest.raises(ValueError):
        project_pixels_to_surveyed_plane(np.asarray(pixels), K, extrinsics, plane)


def test_reject_nonrotation_and_uncalibrated_focal_length():
    bad = CameraExtrinsicsENU((0, 0, 10), ((2., 0., 0.), (0., -1., 0.), (0., 0., -1.)))
    with pytest.raises(ValueError, match="rotation"):
        project_pixels_to_surveyed_plane(np.array([[0., 0.]]), K, bad, SurveyedPlane3D((0, 0, 0), (0, 0, 1)))
    with pytest.raises(ValueError, match="focal"):
        project_pixels_to_surveyed_plane(np.array([[0., 0.]]), PinholeIntrinsics(0, 100, 0, 0), DOWN, SurveyedPlane3D((0, 0, 0), (0, 0, 1)))
