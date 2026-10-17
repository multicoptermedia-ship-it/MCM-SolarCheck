"""Synthetic metric raster extent tests; not a GIS accuracy certification."""
import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_basis import basis_from_surveyed_plane
from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D
from mcm_solarcheck.services.module_surface_grid_planning import plan_surveyed_module_grid

PLANE = SurveyedPlane3D((0, 0, 0), (0, 0, 1))


def test_flat_surveyed_rectangle_uses_metric_extent():
    corners = np.array([[0, 0, 0], [2, 0, 0], [2, 1, 0], [0, 1, 0]])
    grid = plan_surveyed_module_grid(corners, PLANE, metres_per_pixel=0.1)
    assert grid.width == 20
    assert grid.height == 10
    assert grid.u_min_m == 0
    assert grid.v_min_m == 0


def test_tilted_plane_uses_true_surface_not_horizontal_projection():
    normal = np.array([-1., 0., 1.]) / np.sqrt(2)
    plane = SurveyedPlane3D((0, 0, 0), tuple(normal))
    basis = basis_from_surveyed_plane(plane)
    u, v = np.array(basis.axis_u_enu), np.array(basis.axis_v_enu)
    corners = np.array([np.zeros(3), 2*u, 2*u+v, v])
    grid = plan_surveyed_module_grid(corners, plane, metres_per_pixel=0.5)
    assert (grid.width, grid.height) == (4, 2)


def test_reject_off_plane_corners_and_unbounded_grid():
    corners = np.array([[0, 0, 0], [2, 0, 0], [0, 1, 0]])
    with pytest.raises(ValueError, match="plane"):
        plan_surveyed_module_grid(corners + [0, 0, 0.1], PLANE, metres_per_pixel=0.1)
    with pytest.raises(ValueError, match="budget"):
        plan_surveyed_module_grid(corners, PLANE, metres_per_pixel=0.001, max_pixels=100)
