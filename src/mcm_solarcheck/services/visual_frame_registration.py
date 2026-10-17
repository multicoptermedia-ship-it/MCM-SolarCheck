"""Visual registration of adjacent original RGB frames (non-metric)."""
from __future__ import annotations

import cv2
import numpy as np

from mcm_solarcheck.services.visual_homography_gate import validate_visual_homography


def estimate_visual_link(first, second, *, minimum_inliers=12, minimum_ratio=0.3):
    orb = cv2.ORB_create(nfeatures=2000)
    a, da = orb.detectAndCompute(cv2.cvtColor(first, cv2.COLOR_RGB2GRAY), None)
    b, db = orb.detectAndCompute(cv2.cvtColor(second, cv2.COLOR_RGB2GRAY), None)
    if da is None or db is None or len(da) < 2 or len(db) < 2:
        raise ValueError('insufficient visual features')
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da, db, k=2)
    matches = [p[0] for p in pairs if len(p) == 2 and p[0].distance < .75 * p[1].distance]
    if len(matches) < minimum_inliers:
        raise ValueError('insufficient matched visual features')
    src = np.float32([a[m.queryIdx].pt for m in matches])
    dst = np.float32([b[m.trainIdx].pt for m in matches])
    h, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.)
    if h is None or mask is None or int(mask.sum()) < minimum_inliers:
        raise ValueError('unreliable pair alignment')
    validate_visual_homography(h, first.shape[1], first.shape[0])
    if int(mask.sum()) / len(matches) < minimum_ratio:
        raise ValueError('insufficient geometric inlier ratio')
    return h, int(mask.sum())
