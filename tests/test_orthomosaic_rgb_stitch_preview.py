"""RGB stitching preview: real pixels, conservative failures, no ortho claim."""
import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.orthomosaic_rgb_stitch_preview import (
    stitch_rgb_preview, stitch_rgb_series_preview, save_rgb_stitch_preview,
)


def test_overlapping_rgb_images_produce_unverified_preview(tmp_path):
    rng = np.random.default_rng(42)
    base = rng.integers(0, 256, (480, 560, 3), dtype=np.uint8)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    assert cv2.imwrite(str(first), base)
    assert cv2.imwrite(str(second), base)
    result = stitch_rgb_preview(first, second)
    assert result.image.ndim == 3
    assert result.image.shape[1] >= 560
    assert result.inliers >= 20
    assert result.verified_orthomosaic is False


def test_stitch_preview_rejects_invalid_limits(tmp_path):
    with pytest.raises(ValueError, match="resource limits"):
        stitch_rgb_preview(tmp_path / "a", tmp_path / "b", max_side=100)


def test_stitch_preview_rejects_missing_images(tmp_path):
    with pytest.raises(ValueError):
        stitch_rgb_preview(tmp_path / "a.png", tmp_path / "b.png")


def test_three_frame_rgb_preview_and_png_export(tmp_path):
    rng = np.random.default_rng(2026)
    image = rng.integers(0, 256, (480, 560, 3), dtype=np.uint8)
    paths = tuple(tmp_path / f"frame-{i}.png" for i in range(3))
    for path in paths:
        assert cv2.imwrite(str(path), image)
    result = stitch_rgb_series_preview(paths)
    assert result.inliers >= 20
    assert result.verified_orthomosaic is False
    output = save_rgb_stitch_preview(result, tmp_path / "preview.png")
    assert output.is_file()
    assert cv2.imread(str(output)).shape == result.image.shape


def test_series_rejects_duplicate_and_excessive_frames(tmp_path):
    first = tmp_path / "first.png"
    with pytest.raises(ValueError, match="distinct input paths"):
        stitch_rgb_series_preview((first, first))
    with pytest.raises(ValueError, match="frame count"):
        stitch_rgb_series_preview(tuple(tmp_path / f"{i}.png" for i in range(9)))
    with pytest.raises(ValueError, match="max_frames"):
        stitch_rgb_series_preview((first, tmp_path / "second.png"), max_frames=1)


def test_png_export_rejects_unsupported_extension(tmp_path):
    from mcm_solarcheck.services.orthomosaic_rgb_stitch_preview import RGBStitchPreview
    preview = RGBStitchPreview(np.zeros((16, 16, 3), dtype=np.uint8), 20)
    with pytest.raises(ValueError, match="PNG"):
        save_rgb_stitch_preview(preview, tmp_path / "preview.jpg")


def test_invalid_minimum_inliers_rejected_early(tmp_path):
    with pytest.raises(ValueError, match="minimum_inliers"):
        stitch_rgb_preview(tmp_path / "a", tmp_path / "b", minimum_inliers=3)
