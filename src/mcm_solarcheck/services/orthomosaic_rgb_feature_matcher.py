"""Local, bounded ORB/RANSAC overlap evidence from actual RGB image pixels."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from mcm_solarcheck.services.orthomosaic_overlap_graph import PairFeatureEvidence


@dataclass(frozen=True)
class RGBFeatureMatchResult:
    evidence: PairFeatureEvidence
    inlier_fraction: float
    geometrically_plausible: bool
    status: str


def _load_grayscale(path: Path, max_side: int) -> np.ndarray:
    if max_side < 128 or max_side > 4096:
        raise ValueError("max_side must be between 128 and 4096")
    # Decode reduced-resolution images when supported to limit peak memory.
    image = cv2.imread(str(path), cv2.IMREAD_REDUCED_GRAYSCALE_4)
    if image is None:
        raise ValueError("cannot decode RGB image")
    height, width = image.shape[:2]
    if min(height, width) < 32:
        raise ValueError("image too small for feature matching")
    if max(height, width) > max_side:
        scale = max_side / max(height, width)
        image = cv2.resize(image, (max(32, round(width * scale)),
                                    max(32, round(height * scale))), interpolation=cv2.INTER_AREA)
    return image


def match_rgb_feature_pair(
    first_id: str, first_path: str | Path,
    second_id: str, second_path: str | Path,
    *,
    max_side: int = 1200,
    max_features: int = 2500,
    minimum_inliers: int = 20,
    minimum_inlier_fraction: float = 0.25,
) -> RGBFeatureMatchResult:
    if not first_id or not second_id or first_id == second_id:
        raise ValueError("distinct frame ids required")
    if not 100 <= max_features <= 10000:
        raise ValueError("max_features out of bounds")
    if minimum_inliers < 4 or not 0 < minimum_inlier_fraction <= 1:
        raise ValueError("invalid matching thresholds")
    left = _load_grayscale(Path(first_path), max_side)
    right = _load_grayscale(Path(second_path), max_side)
    orb = cv2.ORB_create(nfeatures=max_features)
    points_a, desc_a = orb.detectAndCompute(left, None)
    points_b, desc_b = orb.detectAndCompute(right, None)
    verifier = "orb_mutual_hamming_homography_ransac"
    if desc_a is None or desc_b is None:
        evidence = PairFeatureEvidence(first_id, second_id, 0, 0, verifier)
        return RGBFeatureMatchResult(evidence, 0.0, False, "no_descriptors")
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(matcher.match(desc_a, desc_b), key=lambda m: m.distance)
    # Hamming distance <=64 is a conservative prefilter for 256-bit ORB descriptors.
    matches = [match for match in matches if match.distance <= 64]
    tentative = len(matches)
    inliers = 0
    if tentative >= 4:
        src = np.float32([points_a[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst = np.float32([points_b[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
        if mask is not None:
            inliers = int(np.count_nonzero(mask))
    fraction = inliers / tentative if tentative else 0.0
    plausible = inliers >= minimum_inliers and fraction >= minimum_inlier_fraction
    evidence = PairFeatureEvidence(first_id, second_id, tentative, inliers, verifier)
    return RGBFeatureMatchResult(evidence, fraction, plausible,
                                 "plausible_pair" if plausible else "unverified_pair")
