"""Offline planar orthorectification from original photographs and surveyed controls.

A planar surface model is an explicit limitation: this is not terrain/3D
photogrammetry. Never derive control coordinates from an ORB stitch preview.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from mcm_solarcheck.services.orthomosaic_geotiff_contract import (
    GeoTIFFSpatialReference, validate_geotiff_reference,
)


@dataclass(frozen=True)
class SurveyedFrame:
    image_path: Path
    pixel_points: tuple[tuple[float, float], ...]
    world_points: tuple[tuple[float, float], ...]
    controls_surveyed: bool = False


def rectify_planar_frame(frame: SurveyedFrame, reference: GeoTIFFSpatialReference):
    """Warp one photograph onto a declared GIS grid, returning pixels and coverage.

    Requires >=4 independent surveyed controls and a verified planar target.
    No inferred drone GPS or invented coordinates are accepted.
    """
    validate_geotiff_reference(reference)
    if frame.controls_surveyed is not True:
        raise ValueError("surveyed ground control and planar geometry are required")
    if len(frame.pixel_points) < 4 or len(frame.pixel_points) != len(frame.world_points):
        raise ValueError("at least four matching control points are required")
    pixels = np.asarray(frame.pixel_points, dtype=np.float64)
    world = np.asarray(frame.world_points, dtype=np.float64)
    if pixels.shape != (len(frame.pixel_points), 2) or not np.isfinite(pixels).all() or not np.isfinite(world).all():
        raise ValueError("control coordinates must be finite 2D points")
    if len(np.unique(pixels, axis=0)) < 4 or len(np.unique(world, axis=0)) < 4:
        raise ValueError("control points must be distinct")
    for points in (pixels, world):
        centered = points - points.mean(axis=0)
        singular = np.linalg.svd(centered, compute_uv=False)
        if singular[0] <= 0 or singular[1] / singular[0] < 1e-6:
            raise ValueError("control points must span a non-collinear surface")
    a, b, c, d, e, f = reference.transform
    inverse = np.linalg.inv(np.array([[a, b], [d, e]], dtype=np.float64))
    target_pixels = (world - np.array([c, f])) @ inverse.T
    matrix, mask = cv2.findHomography(pixels, target_pixels, cv2.RANSAC, 2.0)
    if matrix is None or mask is None or int(mask.sum()) < 4 or not np.isfinite(matrix).all():
        raise ValueError("control geometry cannot be rectified")
    predicted = cv2.perspectiveTransform(pixels.reshape(-1, 1, 2), matrix).reshape(-1, 2)
    residual = np.linalg.norm(predicted - target_pixels, axis=1)
    if not np.isfinite(residual).all() or float(np.max(residual)) > 2.0:
        raise ValueError("surveyed control residual exceeds 2 output pixels")
    image = cv2.imread(str(frame.image_path), cv2.IMREAD_UNCHANGED)
    if image is None or image.ndim not in (2, 3):
        raise ValueError("photograph could not be decoded")
    if image.ndim == 3 and image.shape[2] not in (3, 4):
        raise ValueError("unsupported photograph channel count")
    size = (reference.width, reference.height)
    warped = cv2.warpPerspective(image, matrix, size, flags=cv2.INTER_LINEAR)
    coverage = cv2.warpPerspective(
        np.ones(image.shape[:2], dtype=np.uint8), matrix, size,
        flags=cv2.INTER_NEAREST,
    ).astype(bool)
    return warped, coverage
