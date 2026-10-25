"""Synthetic projected-area vs. true PV-module surface-area tests."""
from math import cos, radians, sin

import pytest

from mcm_solarcheck.services.module_plane_projection import SurveyedPlane3D
from mcm_solarcheck.services.rgb_plane_footprint import inspect_rgb_plane_footprint


def plane(tilt):
    a = radians(tilt)
    return SurveyedPlane3D((10, 20, 5), (sin(a), 0., cos(a)))


@pytest.mark.parametrize("tilt", [0, 20, 25, 30, 45, 60])
def test_orthoprojection_foreshortens_true_tilted_area(tilt):
    result = inspect_rgb_plane_footprint(plane(tilt))
    assert result.tilt_from_horizontal_deg == pytest.approx(tilt)
    assert result.horizontal_fraction_of_true_surface == pytest.approx(cos(radians(tilt)))
    assert result.horizontal_to_surface_area_factor == pytest.approx(1 / cos(radians(tilt)))
    assert result.vertical_projection_possible
    assert not result.georeferencing_verified


def test_vertical_plane_requires_own_metric_plane_view():
    result = inspect_rgb_plane_footprint(plane(90))
    assert not result.vertical_projection_possible
    assert result.horizontal_to_surface_area_factor == float("inf")


def test_bad_geometry_fails_closed():
    with pytest.raises(ValueError, match="unit"):
        inspect_rgb_plane_footprint(SurveyedPlane3D((0, 0, 0), (0, 0, 2)))
    with pytest.raises(ValueError, match="finite"):
        inspect_rgb_plane_footprint(SurveyedPlane3D((0, 0, float("nan")), (0, 0, 1)))
