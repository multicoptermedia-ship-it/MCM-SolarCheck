"""Local visual pair mosaic. Perspective preview ONLY, never a metric orthophoto."""
from __future__ import annotations

from dataclasses import dataclass
import cv2
import numpy as np


@dataclass(frozen=True)
class VisualPairMosaic:
    image: np.ndarray
    inliers: int
    preview_only: bool = True

    @property
    def metric_orthophoto_verified(self) -> bool:
        return False


def compose_visual_pair(first: np.ndarray, second: np.ndarray, *, max_pixels=12_000_000, minimum_inliers=12, minimum_inlier_ratio=0.3) -> VisualPairMosaic:
    """Estimate first-to-second image homography and blend overlapping RGB pixels.

    Output is a non-metric, unreferenced visual preview; no roof-area or temperature claims.
    """
    if not isinstance(first, np.ndarray) or not isinstance(second, np.ndarray):
        raise ValueError("two RGB numpy arrays required")
    if any(a.dtype != np.uint8 or a.ndim != 3 or a.shape[2] != 3 or min(a.shape[:2]) < 128 for a in (first, second)):
        raise ValueError("two uint8 RGB images of at least 128x128 required")
    if type(max_pixels) is not int or max_pixels < 1 or type(minimum_inliers) is not int or minimum_inliers < 4:
        raise ValueError("invalid mosaic limits")
    if not isinstance(minimum_inlier_ratio, (float, int)) or not 0 < minimum_inlier_ratio <= 1:
        raise ValueError("invalid inlier ratio threshold")
    orb = cv2.ORB_create(nfeatures=2000)
    gray_a = cv2.cvtColor(first, cv2.COLOR_RGB2GRAY)
    gray_b = cv2.cvtColor(second, cv2.COLOR_RGB2GRAY)
    pts_a, desc_a = orb.detectAndCompute(gray_a, None)
    pts_b, desc_b = orb.detectAndCompute(gray_b, None)
    if desc_a is None or desc_b is None or len(desc_a) < 2 or len(desc_b) < 2:
        raise ValueError("insufficient visual features")
    matches = []
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    for pair in matcher.knnMatch(desc_a, desc_b, k=2):
        if len(pair) == 2 and pair[0].distance < .75 * pair[1].distance:
            matches.append(pair[0])
    if len(matches) < max(4, minimum_inliers):
        raise ValueError("insufficient matched visual features")
    src = np.float32([pts_a[m.queryIdx].pt for m in matches])
    dst = np.float32([pts_b[m.trainIdx].pt for m in matches])
    matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    if matrix is None or mask is None or int(mask.sum()) < minimum_inliers or not np.isfinite(matrix).all():
        raise ValueError("unreliable pair alignment")
    from mcm_solarcheck.services.visual_homography_gate import validate_visual_homography
    validate_visual_homography(matrix, first.shape[1], first.shape[0])
    if int(mask.sum()) / len(matches) < minimum_inlier_ratio:
        raise ValueError("insufficient geometric inlier ratio")
    def corners(a):
        h, w = a.shape[:2]
        return np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(corners(first), matrix).reshape(-1, 2)
    all_points = np.vstack((projected, corners(second).reshape(-1, 2)))
    if not np.isfinite(all_points).all():
        raise ValueError("invalid projected bounds")
    low = np.floor(all_points.min(axis=0)).astype(int)
    high = np.ceil(all_points.max(axis=0)).astype(int)
    width, height = (high - low).tolist()
    if width <= 0 or height <= 0 or width * height > max_pixels:
        raise ValueError("visual mosaic exceeds canvas limit")
    offset = np.array([[1., 0., -low[0]], [0., 1., -low[1]], [0., 0., 1.]])
    warped_a = cv2.warpPerspective(first, offset @ matrix, (width, height))
    mask_a = cv2.warpPerspective(np.ones(first.shape[:2], dtype=np.uint8), offset @ matrix, (width, height)) > 0
    warped_b = cv2.warpPerspective(second, offset, (width, height))
    mask_b = cv2.warpPerspective(np.ones(second.shape[:2], dtype=np.uint8), offset, (width, height)) > 0
    count = mask_a.astype(np.uint8) + mask_b.astype(np.uint8)
    combined = np.zeros_like(warped_a)
    valid = count > 0
    summed = warped_a.astype(np.uint16) * mask_a[..., None] + warped_b.astype(np.uint16) * mask_b[..., None]
    combined[valid] = (summed[valid] // count[valid, None]).astype(np.uint8)
    return VisualPairMosaic(combined, int(mask.sum()))
