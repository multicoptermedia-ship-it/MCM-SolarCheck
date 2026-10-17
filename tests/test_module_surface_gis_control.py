"""Synthetic control-fit diagnostics do not certify survey georeferencing."""
import numpy as np
import pytest

from mcm_solarcheck.services.module_surface_gis_control import audit_surface_gis_controls

UV = np.array([[0., 0.], [2., 0.], [0., 1.], [2., 1.], [1., 0.5]])
XY = np.column_stack((500000 + 2 * UV[:, 0], 5600000 + 3 * UV[:, 1]))


def test_exact_metric_survey_control_fit_is_diagnostic_only():
    transform, audit = audit_surface_gis_controls(UV, XY, tolerance_m=0.01)
    np.testing.assert_allclose(transform, (2, 0, 500000, 0, 3, 5600000), atol=1e-7)
    assert audit.within_tolerance
    assert audit.control_count == 5
    assert not audit.independently_verified


def test_inconsistent_control_fails_tolerance_without_false_certification():
    inconsistent = XY.copy()
    inconsistent[-1, 0] += 1.
    _, audit = audit_surface_gis_controls(UV, inconsistent, tolerance_m=0.01)
    assert not audit.within_tolerance
    assert not audit.independently_verified


def test_duplicate_and_collinear_controls_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        audit_surface_gis_controls(np.vstack((UV[:4], UV[0])), XY, tolerance_m=0.1)
    line = np.column_stack((np.arange(4.), np.zeros(4)))
    with pytest.raises(ValueError, match="two-dimensional"):
        audit_surface_gis_controls(line, line + 100, tolerance_m=0.1)
