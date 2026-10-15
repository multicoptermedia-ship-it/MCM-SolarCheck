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
    assert 0.0 < result.covered_fraction <= 1.0


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


def test_black_pixels_count_as_covered_image_area(tmp_path):
    rng = np.random.default_rng(99)
    base = rng.integers(0, 256, (480, 560, 3), dtype=np.uint8)
    base[100:220, 100:220] = 0
    first, second = tmp_path / "a.png", tmp_path / "b.png"
    assert cv2.imwrite(str(first), base)
    assert cv2.imwrite(str(second), base)
    result = stitch_rgb_preview(first, second)
    assert result.covered_fraction > 0.95
    assert result.verified_orthomosaic is False


def test_unrelated_rgb_images_rejected(tmp_path):
    rng = np.random.default_rng(1337)
    first, second = tmp_path / "a.png", tmp_path / "b.png"
    assert cv2.imwrite(str(first), rng.integers(0, 256, (480, 560, 3), dtype=np.uint8))
    assert cv2.imwrite(str(second), rng.integers(0, 256, (480, 560, 3), dtype=np.uint8))
    with pytest.raises(ValueError):
        stitch_rgb_preview(first, second)


def test_shifted_rgb_crops_with_real_shared_pixels(tmp_path):
    rng = np.random.default_rng(20261015)
    scene = rng.integers(0, 256, (480, 760, 3), dtype=np.uint8)
    left, right = tmp_path / "left.png", tmp_path / "right.png"
    assert cv2.imwrite(str(left), scene[:, :560])
    assert cv2.imwrite(str(right), scene[:, 80:640])
    result = stitch_rgb_preview(left, right)
    assert result.image.shape[1] >= 560
    assert result.inliers >= 20
    assert result.median_reprojection_error_px is not None
    assert result.median_reprojection_error_px <= 3.0
    assert result.verified_orthomosaic is False


def test_manifest_contains_explicit_unverified_provenance(tmp_path):
    import json
    from mcm_solarcheck.services.orthomosaic_rgb_stitch_preview import (
        RGBStitchPreview, save_rgb_preview_manifest,
    )
    preview = RGBStitchPreview(
        np.zeros((32, 48, 3), dtype=np.uint8), 31,
        covered_fraction=0.85, median_reprojection_error_px=0.7,
    )
    manifest = save_rgb_preview_manifest(
        preview, tmp_path / "preview.json", source_names=("a.png", "b.png"),
    )
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["verified_orthomosaic"] is False
    assert data["status"] == "unverified_preview"
    assert data["canvas_covered_fraction"] == 0.85
    assert data["last_pair_median_reprojection_error_px"] == 0.7
    with pytest.raises(ValueError, match="safe basenames"):
        save_rgb_preview_manifest(preview, tmp_path / "bad.json", source_names=("../private.png",))


def test_paired_artifacts_written_locally_and_not_overwritten(tmp_path):
    import json
    from mcm_solarcheck.services.orthomosaic_rgb_stitch_preview import (
        RGBStitchPreview, save_rgb_preview_artifacts,
    )
    preview = RGBStitchPreview(
        np.zeros((48, 64, 3), dtype=np.uint8), 24,
        covered_fraction=1.0, median_reprojection_error_px=0.2,
    )
    image, manifest = save_rgb_preview_artifacts(
        preview, tmp_path, source_names=("frame-1.png", "frame-2.png"),
    )
    assert image.is_file() and manifest.is_file()
    assert cv2.imread(str(image)).shape == (48, 64, 3)
    assert json.loads(manifest.read_text(encoding="utf-8"))["verified_orthomosaic"] is False
    with pytest.raises(FileExistsError):
        save_rgb_preview_artifacts(preview, tmp_path, source_names=("frame-1.png",))


def test_manifest_rejects_nan_and_infinite_diagnostics(tmp_path):
    from mcm_solarcheck.services.orthomosaic_rgb_stitch_preview import (
        RGBStitchPreview, save_rgb_preview_manifest,
    )
    for value in (float("nan"), float("inf"), -0.1):
        preview = RGBStitchPreview(np.zeros((16, 16, 3), dtype=np.uint8), 20,
                                   covered_fraction=value)
        with pytest.raises(ValueError, match="coverage"):
            save_rgb_preview_manifest(preview, tmp_path / "invalid.json",
                                      source_names=("frame.png",))
    preview = RGBStitchPreview(np.zeros((16, 16, 3), dtype=np.uint8), 20,
                               covered_fraction=1.0,
                               median_reprojection_error_px=float("nan"))
    with pytest.raises(ValueError, match="reprojection"):
        save_rgb_preview_manifest(preview, tmp_path / "invalid.json",
                                  source_names=("frame.png",))
