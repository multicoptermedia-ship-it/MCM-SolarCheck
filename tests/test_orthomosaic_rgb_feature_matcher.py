from pathlib import Path

import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.orthomosaic_rgb_feature_matcher import match_rgb_feature_pair
from mcm_solarcheck.services.orthomosaic_rgb_overlap_batch import inspect_rgb_neighbor_pairs


def test_real_pixel_matches_on_identical_textured_image(tmp_path: Path):
    rng = np.random.default_rng(12)
    image = rng.integers(0, 256, size=(500, 600), dtype=np.uint8)
    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    assert cv2.imwrite(str(first), image)
    assert cv2.imwrite(str(second), image)
    result = match_rgb_feature_pair("a", first, "b", second)
    assert result.geometrically_plausible
    assert result.evidence.verified_inliers >= 20
    batch = inspect_rgb_neighbor_pairs((("a", first), ("b", second)))
    assert batch.connectivity.connected
    assert not batch.project_overlap_verified


def test_blank_images_do_not_fabricate_matches(tmp_path: Path):
    path = tmp_path / "blank.png"
    assert cv2.imwrite(str(path), np.zeros((400, 400), dtype=np.uint8))
    result = match_rgb_feature_pair("a", path, "b", path)
    assert not result.geometrically_plausible
    assert result.evidence.verified_inliers == 0


def test_bad_images_and_invalid_thresholds_fail_closed(tmp_path: Path):
    missing = tmp_path / "missing.jpg"
    with pytest.raises(ValueError):
        match_rgb_feature_pair("a", missing, "b", missing)
    with pytest.raises(ValueError):
        match_rgb_feature_pair("a", missing, "a", missing)
    with pytest.raises(ValueError):
        match_rgb_feature_pair("a", missing, "b", missing, max_features=0)
