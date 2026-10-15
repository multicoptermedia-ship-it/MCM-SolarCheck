"""Bounded, local two-frame RGB stitching prototype.

This is an UNVERIFIED planar preview, never an orthomosaic. Camera calibration,
module-plane rectification, flight coverage and thermal registration are separate.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from mcm_solarcheck.services.orthomosaic_rgb_feature_matcher import match_rgb_feature_pair


@dataclass(frozen=True)
class RGBStitchPreview:
    image: np.ndarray
    inliers: int
    verified_orthomosaic: bool = False
    covered_fraction: float = 0.0
    median_reprojection_error_px: float | None = None


def stitch_rgb_preview(
    first_path: str | Path,
    second_path: str | Path,
    *,
    max_side: int = 1400,
    max_canvas_pixels: int = 12_000_000,
    minimum_inliers: int = 20,
) -> RGBStitchPreview:
    """Create a memory-bounded diagnostic mosaic from two real RGB photographs."""
    if not 128 <= max_side <= 4096 or max_canvas_pixels < 100_000:
        raise ValueError("invalid preview resource limits")
    if minimum_inliers < 4:
        raise ValueError("minimum_inliers must be at least four")
    first_path, second_path = Path(first_path), Path(second_path)
    preliminary = match_rgb_feature_pair(
        "first", first_path, "second", second_path,
        max_side=max_side, minimum_inliers=minimum_inliers,
    )
    if not preliminary.geometrically_plausible:
        raise ValueError("RGB images do not have verified pairwise overlap")

    def read(path: Path) -> np.ndarray:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("cannot decode RGB image")
        h, w = image.shape[:2]
        if max(h, w) > max_side:
            factor = max_side / max(h, w)
            image = cv2.resize(image, (round(w * factor), round(h * factor)),
                               interpolation=cv2.INTER_AREA)
        return image

    left, right = read(first_path), read(second_path)
    orb = cv2.ORB_create(nfeatures=3000)
    points_a, desc_a = orb.detectAndCompute(cv2.cvtColor(left, cv2.COLOR_BGR2GRAY), None)
    points_b, desc_b = orb.detectAndCompute(cv2.cvtColor(right, cv2.COLOR_BGR2GRAY), None)
    if desc_a is None or desc_b is None:
        raise ValueError("RGB features missing")
    matches = [m for m in cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(desc_b, desc_a)
               if m.distance <= 64]
    if len(matches) < minimum_inliers:
        raise ValueError("insufficient RGB correspondences")
    src = np.float32([points_b[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst = np.float32([points_a[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    if matrix is None or mask is None or int(np.count_nonzero(mask)) < minimum_inliers:
        raise ValueError("RGB alignment could not be verified")
    projected = cv2.perspectiveTransform(src, matrix).reshape(-1, 2)
    errors = np.linalg.norm(projected - dst.reshape(-1, 2), axis=1)
    inlier_errors = errors[mask.ravel().astype(bool)]
    if not np.isfinite(inlier_errors).all() or float(np.median(inlier_errors)) > 3.0:
        raise ValueError("RGB alignment residual exceeds tolerance")
    h1, w1 = left.shape[:2]
    h2, w2 = right.shape[:2]
    corners = np.float32([[0, 0], [w2, 0], [w2, h2], [0, h2]]).reshape(-1, 1, 2)
    transformed = cv2.perspectiveTransform(corners, matrix).reshape(-1, 2)
    all_points = np.vstack((transformed, [[0, 0], [w1, 0], [w1, h1], [0, h1]]))
    if not np.isfinite(all_points).all():
        raise ValueError("nonfinite image transformation")
    transformed_area = float(cv2.contourArea(transformed.astype(np.float32)))
    source_area = float(w2 * h2)
    if not 0.25 * source_area <= transformed_area <= 4.0 * source_area:
        raise ValueError("implausible RGB transform scale")
    low = np.floor(all_points.min(axis=0)).astype(np.int64)
    high = np.ceil(all_points.max(axis=0)).astype(np.int64)
    width, height = map(int, high - low)
    if width < 1 or height < 1 or width * height > max_canvas_pixels:
        raise ValueError("stitching canvas exceeds resource limits")
    translate = np.array([[1., 0., -float(low[0])], [0., 1., -float(low[1])], [0., 0., 1.]])
    canvas = cv2.warpPerspective(right, translate @ matrix, (width, height))
    right_mask = cv2.warpPerspective(np.ones((h2, w2), dtype=np.uint8),
                                     translate @ matrix, (width, height),
                                     flags=cv2.INTER_NEAREST)
    x, y = map(int, -low)
    # Deterministic priority to the reference photograph in overlapping regions.
    canvas[y:y+h1, x:x+w1] = left
    right_mask[y:y+h1, x:x+w1] = 1
    coverage = float(np.count_nonzero(right_mask)) / (width * height)
    return RGBStitchPreview(canvas, int(np.count_nonzero(mask)), covered_fraction=coverage,
                            median_reprojection_error_px=float(np.median(inlier_errors)))


def save_rgb_stitch_preview(preview: RGBStitchPreview, output_path: str | Path) -> Path:
    """Write a diagnostic PNG locally; never mark it as a verified orthomosaic."""
    path = Path(output_path)
    if path.suffix.lower() != ".png":
        raise ValueError("preview output must be PNG")
    if preview.verified_orthomosaic:
        raise ValueError("verified orthomosaics require a separate export path")
    if preview.image.ndim != 3 or preview.image.shape[2] != 3 or preview.image.dtype != np.uint8:
        raise ValueError("preview must be an 8-bit BGR image")
    if not path.parent.is_dir():
        raise ValueError("output directory does not exist")
    if not cv2.imwrite(str(path), preview.image):
        raise OSError("could not write RGB preview")
    return path


def stitch_rgb_series_preview(
    image_paths: tuple[str | Path, ...],
    *,
    max_frames: int = 8,
    max_side: int = 1400,
    max_canvas_pixels: int = 12_000_000,
    minimum_inliers: int = 20,
) -> RGBStitchPreview:
    """Sequentially stitch a small local series; diagnostic preview only.

    This intentionally does not claim flight-wide coverage or georectification.
    Every adjacent composition must pass the existing pixel-overlap gate.
    """
    from tempfile import TemporaryDirectory

    if not 2 <= max_frames <= 32:
        raise ValueError("max_frames must be between 2 and 32")
    if not 2 <= len(image_paths) <= max_frames:
        raise ValueError("RGB series frame count outside configured limit")
    paths = tuple(Path(path) for path in image_paths)
    if len(set(paths)) != len(paths):
        raise ValueError("RGB series must contain distinct input paths")
    with TemporaryDirectory(prefix="mcm-rgb-preview-") as directory:
        result = stitch_rgb_preview(
            paths[0], paths[1], max_side=max_side,
            max_canvas_pixels=max_canvas_pixels, minimum_inliers=minimum_inliers,
        )
        min_pair_inliers = result.inliers
        for index, path in enumerate(paths[2:], start=2):
            previous = Path(directory) / f"stage-{index}.png"
            save_rgb_stitch_preview(result, previous)
            result = stitch_rgb_preview(
                previous, path, max_side=max_side,
                max_canvas_pixels=max_canvas_pixels, minimum_inliers=minimum_inliers,
            )
            min_pair_inliers = min(min_pair_inliers, result.inliers)
    return RGBStitchPreview(result.image, min_pair_inliers,
                            covered_fraction=result.covered_fraction,
                            median_reprojection_error_px=result.median_reprojection_error_px)


def save_rgb_preview_manifest(
    preview: RGBStitchPreview,
    output_path: str | Path,
    *,
    source_names: tuple[str, ...],
) -> Path:
    """Persist non-sensitive diagnostic metadata beside a local preview."""
    import json

    path = Path(output_path)
    if path.suffix.lower() != ".json" or not path.parent.is_dir():
        raise ValueError("manifest requires an existing directory and JSON extension")
    if not source_names or len(source_names) > 32 or any(
        not name or Path(name).name != name for name in source_names
    ):
        raise ValueError("source_names must be safe basenames")
    if preview.verified_orthomosaic:
        raise ValueError("unverified preview manifest only")
    if not 0.0 <= preview.covered_fraction <= 1.0:
        raise ValueError("invalid canvas coverage")
    payload = {
        "schema": "mcm.rgb_preview.v1",
        "status": "unverified_preview",
        "verified_orthomosaic": False,
        "source_names": list(source_names),
        "minimum_pair_inliers": preview.inliers,
        "canvas_covered_fraction": preview.covered_fraction,
        "last_pair_median_reprojection_error_px": preview.median_reprojection_error_px,
        "image_width": int(preview.image.shape[1]),
        "image_height": int(preview.image.shape[0]),
    }
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\\n", encoding="utf-8")
    return path
