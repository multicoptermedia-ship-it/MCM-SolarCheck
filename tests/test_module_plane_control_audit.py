"""Synthetic held-out surveyed control audit for calibrated camera projection."""
import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_control_audit import audit_surveyed_plane_controls
from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D,
    project_pixels_to_surveyed_plane,
)

K = PinholeIntrinsics(100, 100, 0, 0)
CAMERA = CameraExtrinsicsENU((0, 0, 10), ((1., 0., 0.), (0., -1., 0.), (0., 0., -1.)))
NORMAL = tuple(np.array([-1., 0., 1.]) / np.sqrt(2))
PLANE = SurveyedPlane3D((0, 0, 0), NORMAL)
PIXELS = np.array([[0., 0.], [10., 0.], [10., 10.], [0., 10.]])
SURVEY = project_pixels_to_surveyed_plane(PIXELS, K, CAMERA, PLANE)


def test_exact_independent_surveyed_controls_pass_but_not_certified():
    audit = audit_surveyed_plane_controls(PIXELS, SURVEY, K, CAMERA, PLANE, tolerance_m=0.01)
    assert audit.count == 4
    assert audit.within_tolerance
    assert audit.rms_error_m < 1e-9
    assert not audit.independently_verified


def test_perturbed_control_reports_failed_tolerance():
    perturbed = SURVEY.copy()
    perturbed[1] += [0., 0.05, 0.]
    audit = audit_surveyed_plane_controls(PIXELS, perturbed, K, CAMERA, PLANE, tolerance_m=0.01)
    assert not audit.within_tolerance
    assert audit.max_error_m > 0.04


def test_reject_collinear_controls():
    pixels = np.array([[0., 0.], [5., 0.], [10., 0.], [15., 0.]])
    surveyed = project_pixels_to_surveyed_plane(pixels, K, CAMERA, PLANE)
    with pytest.raises(ValueError, match="two surface directions"):
        audit_surveyed_plane_controls(pixels, surveyed, K, CAMERA, PLANE, tolerance_m=0.01)
