"""Deterministic pixel-space visual loop consistency tests."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_loop_consistency import visual_loop_error, require_visual_loop


def test_identical_transforms_have_zero_loop_error():
    identity = np.eye(3)
    assert visual_loop_error(identity, identity, 800, 600) == 0.0
    assert require_visual_loop(identity, identity, 800, 600) == 0.0


def test_disagreeing_translations_are_detected():
    identity = np.eye(3)
    translated = np.array([[1., 0., 25.], [0., 1., 0.], [0., 0., 1.]])
    assert visual_loop_error(identity, translated, 800, 600) == pytest.approx(25.)
    with pytest.raises(ValueError, match="inconsistent"):
        require_visual_loop(identity, translated, 800, 600)


def test_nonfinite_matrix_is_rejected():
    bad = np.eye(3)
    bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="invalid loop"):
        visual_loop_error(bad, np.eye(3), 800, 600)


def test_bad_threshold_is_rejected():
    with pytest.raises(ValueError, match="threshold"):
        require_visual_loop(np.eye(3), np.eye(3), 800, 600, max_error_px=0)
