"""Synthetic overlap intensity diagnostics for RGB and thermal-display arrays."""
import numpy as np
import pytest

from mcm_solarcheck.services.visual_overlap_quality import assess_visual_overlap


@pytest.mark.parametrize("channels", [1, 3])
def test_identical_visual_overlap_has_zero_disagreement(channels):
    im = np.full((4, 5), 90, dtype=np.uint8)
    if channels == 3:
        im = np.repeat(im[..., None], 3, axis=2)
    mask = np.ones((4, 5), dtype=np.uint8)
    q = assess_visual_overlap([im, im.copy()], [mask, mask])
    assert q.covered_pixels == q.multiply_covered_pixels == 20
    assert q.mean_overlap_disagreement == 0.
    assert q.max_overlap_disagreement == 0.
    assert not q.metric_accuracy_verified


def test_difference_is_not_mislabeled_as_reprojection_error():
    black = np.zeros((3, 4), dtype=np.uint8)
    white = np.full((3, 4), 200, dtype=np.uint8)
    mask = np.ones((3, 4), dtype=np.uint8)
    q = assess_visual_overlap([black, white], [mask, mask])
    assert q.mean_overlap_disagreement == pytest.approx(100.)
    assert q.max_overlap_disagreement == pytest.approx(100.)


def test_no_overlap_is_explicitly_unknown():
    im = np.ones((2, 2), dtype=np.uint8)
    a = np.array([[1, 0], [0, 0]], dtype=np.uint8)
    b = np.array([[0, 1], [0, 0]], dtype=np.uint8)
    q = assess_visual_overlap([im, im], [a, b])
    assert q.covered_pixels == 2
    assert q.multiply_covered_pixels == 0
    assert q.mean_overlap_disagreement is None


def test_bad_masks_fail_closed():
    im = np.ones((2, 2), dtype=np.uint8)
    with pytest.raises(ValueError, match="binary"):
        assess_visual_overlap([im, im], [np.full((2, 2), 255, dtype=np.uint8)] * 2)
