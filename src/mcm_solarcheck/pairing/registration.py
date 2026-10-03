"""Validated pixel registration from thermal to RGB coordinates.

Transform estimation and validation are deliberately separated. A homography is
fit from training correspondences, while acceptance is based on independent
holdout points so fit residuals cannot masquerade as validation evidence.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
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

def estimate_homography(fit_points:tuple[ControlPoint,...],validation_points:tuple[ControlPoint,...],*,thermal_size:tuple[int,int]=(640,512),rgb_size:tuple[int,int]=(4000,3000),ransac_threshold_px:float=8.0,minimum_fit_points:int=6,minimum_validation_points:int=4,maximum_rms_error_px:float=12.0,maximum_error_px:float=30.0)->HomographyEstimate:
    """Fit with RANSAC and expose a PixelTransform only after holdout validation."""
    if len(fit_points)<minimum_fit_points:
        q=RegistrationQuality(len(validation_points),float('inf'),float('inf'),False,'insufficient_fit_points')
        return HomographyEstimate(PixelTransform('homography_ransac',False,*thermal_size,*rgb_size),q,len(fit_points),0)
    src=np.float64([[p.thermal_x,p.thermal_y] for p in fit_points]);dst=np.float64([[p.rgb_x,p.rgb_y] for p in fit_points])
    matrix,mask=cv2.findHomography(src,dst,cv2.RANSAC,ransac_threshold_px)
    if matrix is None:
        q=RegistrationQuality(len(validation_points),float('inf'),float('inf'),False,'homography_estimation_failed')
        return HomographyEstimate(PixelTransform('homography_ransac',False,*thermal_size,*rgb_size),q,len(fit_points),0)
    flat=tuple(float(v) for v in matrix.reshape(-1));quality=assess_registration(flat,validation_points,minimum_points=minimum_validation_points,maximum_rms_error_px=maximum_rms_error_px,maximum_error_px=maximum_error_px)
    inliers=int(mask.sum()) if mask is not None else 0
    nested=tuple(tuple(float(v) for v in row) for row in matrix)
    transform=PixelTransform('homography_ransac_holdout',quality.validated,*thermal_size,*rgb_size,nested,quality.rms_error_px if quality.validated else None)
    return HomographyEstimate(transform,quality,len(fit_points),inliers)
