"""Synthetic inclined plane metric-coordinate regression checks."""
import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_basis import basis_from_surveyed_plane, plane_coordinates
from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D


def test_horizontal_plane_has_east_north_metric_axes():
    basis = basis_from_surveyed_plane(SurveyedPlane3D((10, 20, 30), (0, 0, 1)))
    xy = plane_coordinates(np.array([[10, 20, 30], [12, 23, 30]]), basis)
    np.testing.assert_allclose(xy, [[0, 0], [2, 3]], atol=1e-10)


def test_inclined_plane_preserves_true_surface_distance():
    normal = np.array([-1., 0., 1.]) / np.sqrt(2)
    basis = basis_from_surveyed_plane(SurveyedPlane3D((0, 0, 0), tuple(normal)))
    u, v = np.asarray(basis.axis_u_enu), np.asarray(basis.axis_v_enu)
    xy = plane_coordinates(np.array([np.zeros(3), 2*u+3*v]), basis)
    np.testing.assert_allclose(xy, [[0, 0], [2, 3]], atol=1e-10)
    assert np.isclose(np.linalg.norm(2*u+3*v), np.sqrt(13))


def test_rejects_off_plane_points():
    basis = basis_from_surveyed_plane(SurveyedPlane3D((0, 0, 0), (0, 0, 1)))
    with pytest.raises(ValueError, match="not on"):
        plane_coordinates(np.array([[1., 2., 0.1]]), basis)
