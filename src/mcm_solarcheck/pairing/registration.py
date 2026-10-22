"""Validated pixel registration from thermal to RGB coordinates.

Transform estimation and validation are deliberately separated. A homography is
fit from training correspondences, while acceptance is based on independent
holdout points so fit residuals cannot masquerade as validation evidence.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, sqrt
import cv2
import numpy as np
from .geometry import PixelTransform

@dataclass(frozen=True)
class ControlPoint:
    thermal_x:float;thermal_y:float;rgb_x:float;rgb_y:float

@dataclass(frozen=True)
class RegistrationQuality:
    control_points:int;rms_error_px:float;max_error_px:float;validated:bool;reason:str

@dataclass(frozen=True)
class HomographyEstimate:
    transform:PixelTransform
    quality:RegistrationQuality
    fit_points:int
    inliers:int

def project_homography(matrix:tuple[float,...],x:float,y:float)->tuple[float,float]:
    if len(matrix)!=9:raise ValueError('homography must contain 9 values')
    a,b,c,d,e,f,g,h,i=matrix;w=g*x+h*y+i
    if abs(w)<1e-12:raise ValueError('point projects to infinity')
    return ((a*x+b*y+c)/w,(d*x+e*y+f)/w)

def assess_registration(matrix:tuple[float,...],points:tuple[ControlPoint,...],*,minimum_points:int=6,maximum_rms_error_px:float=12.0,maximum_error_px:float=30.0)->RegistrationQuality:
    if len(points)<minimum_points:return RegistrationQuality(len(points),float('inf'),float('inf'),False,'insufficient_control_points')
    errors=[]
    for p in points:
        x,y=project_homography(matrix,p.thermal_x,p.thermal_y);errors.append(sqrt((x-p.rgb_x)**2+(y-p.rgb_y)**2))
    rms=sqrt(sum(v*v for v in errors)/len(errors));mx=max(errors);valid=rms<=maximum_rms_error_px and mx<=maximum_error_px
    return RegistrationQuality(len(points),rms,mx,valid,'accepted' if valid else 'reprojection_error_too_high')

def estimate_homography(fit_points:tuple[ControlPoint,...],validation_points:tuple[ControlPoint,...],*,thermal_size:tuple[int,int]=(640,512),rgb_size:tuple[int,int]=(4000,3000),ransac_threshold_px:float=8.0,minimum_fit_points:int=6,minimum_validation_points:int=4,maximum_rms_error_px:float=12.0,maximum_error_px:float=30.0,require_in_bounds:bool=False)->HomographyEstimate:
    """Fit RANSAC only on bounded, independent, non-degenerate correspondences.

    The returned transform is a technical holdout-gated pixel hypothesis only.
    A real sensor registration requires independently reviewed correspondences.
    """
    def refused(reason: str, count: int = 0) -> HomographyEstimate:
        q = RegistrationQuality(
            len(validation_points), float("inf"), float("inf"), False, reason
        )
        return HomographyEstimate(
            PixelTransform("homography_ransac", False, *thermal_size, *rgb_size),
            q, len(fit_points), count,
        )

    if (len(fit_points) < max(4, minimum_fit_points)
            or minimum_fit_points < 4):
        return refused("insufficient_fit_points")
    if (len(validation_points) < max(4, minimum_validation_points)
            or minimum_validation_points < 4):
        return refused("insufficient_control_points")
    if (len(thermal_size) != 2 or len(rgb_size) != 2
            or any(type(n) is not int or n < 2 for n in (*thermal_size, *rgb_size))):
        raise ValueError("Positive sensor image dimensions required")
    if (not isfinite(ransac_threshold_px) or ransac_threshold_px <= 0
            or not isfinite(maximum_rms_error_px) or maximum_rms_error_px <= 0
            or not isfinite(maximum_error_px) or maximum_error_px <= 0):
        raise ValueError("Positive finite registration limits required")

    def coords(points):
        return np.float64([
            [p.thermal_x, p.thermal_y, p.rgb_x, p.rgb_y] for p in points
        ])

    all_fit, all_holdout = coords(fit_points), coords(validation_points)
    if not (np.isfinite(all_fit).all() and np.isfinite(all_holdout).all()):
        return refused("nonfinite_control_points")
    def bounded(arr):
        return bool(
            (arr[:, 0] >= 0).all() and (arr[:, 0] < thermal_size[0]).all()
            and (arr[:, 1] >= 0).all() and (arr[:, 1] < thermal_size[1]).all()
            and (arr[:, 2] >= 0).all() and (arr[:, 2] < rgb_size[0]).all()
            and (arr[:, 3] >= 0).all() and (arr[:, 3] < rgb_size[1]).all()
        )
    # Automatic PV grid intersections may lie outside raster edges. Only
    # explicitly supplied *manual* controls enforce native sensor bounds.
    if require_in_bounds and (not bounded(all_fit) or not bounded(all_holdout)):
        return refused("control_points_out_of_bounds")

    src = all_fit[:, :2]
    dst = all_fit[:, 2:]
    holdout_src = all_holdout[:, :2]
    if (len(np.unique(src, axis=0)) != len(src)
            or len(np.unique(dst, axis=0)) != len(dst)):
        return refused("duplicate_fit_points")
    if (set(map(tuple, src)) & set(map(tuple, holdout_src))):
        return refused("fit_holdout_overlap")
    if (np.linalg.matrix_rank(src - src.mean(axis=0)) < 2
            or np.linalg.matrix_rank(dst - dst.mean(axis=0)) < 2):
        return refused("degenerate_fit_geometry")

    try:
        matrix, mask = cv2.findHomography(
            src, dst, cv2.RANSAC, ransac_threshold_px
        )
    except cv2.error:
        return refused("homography_estimation_failed")
    if matrix is None or not np.isfinite(matrix).all():
        return refused("homography_estimation_failed")
    flat = tuple(float(v) for v in matrix.reshape(-1))
    inliers = int(mask.sum()) if mask is not None else 0
    if inliers < max(4, minimum_fit_points):
        return refused("insufficient_inliers", inliers)
    try:
        quality = assess_registration(
            flat, validation_points,
            minimum_points=minimum_validation_points,
            maximum_rms_error_px=maximum_rms_error_px,
            maximum_error_px=maximum_error_px,
        )
        if not isfinite(quality.rms_error_px) or not isfinite(quality.max_error_px):
            return refused("invalid_holdout_projection", inliers)
        # Reject a projection that becomes undefined at the source-image boundary.
        corners = ((0, 0), (thermal_size[0] - 1, 0),
                   (0, thermal_size[1] - 1),
                   (thermal_size[0] - 1, thermal_size[1] - 1))
        if not all(
            isfinite(x) and isfinite(y)
            for c in corners for x, y in (project_homography(flat, *c),)
        ):
            return refused("invalid_image_corner_projection", inliers)
    except (ValueError, OverflowError, ZeroDivisionError):
        return refused("invalid_holdout_projection", inliers)
    nested = tuple(tuple(float(v) for v in row) for row in matrix)
    transform = PixelTransform(
        "homography_ransac_holdout", quality.validated,
        *thermal_size, *rgb_size, nested,
        quality.rms_error_px if quality.validated else None,
    )
    return HomographyEstimate(transform, quality, len(fit_points), inliers)
