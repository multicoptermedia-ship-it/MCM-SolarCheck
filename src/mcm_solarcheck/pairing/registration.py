"""Validated pixel registration from thermal to RGB coordinates.

Correspondence extraction is deliberately separate from acceptance: a transform
is only exposed as validated after enough control points and bounded residuals.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt

@dataclass(frozen=True)
class ControlPoint:
    thermal_x: float
    thermal_y: float
    rgb_x: float
    rgb_y: float

@dataclass(frozen=True)
class RegistrationQuality:
    control_points: int
    rms_error_px: float
    max_error_px: float
    validated: bool
    reason: str

def project_homography(matrix: tuple[float,...], x: float, y: float) -> tuple[float,float]:
    if len(matrix)!=9: raise ValueError('homography must contain 9 values')
    a,b,c,d,e,f,g,h,i=matrix
    w=g*x+h*y+i
    if abs(w)<1e-12: raise ValueError('point projects to infinity')
    return ((a*x+b*y+c)/w,(d*x+e*y+f)/w)

def assess_registration(matrix:tuple[float,...], points:tuple[ControlPoint,...], *, minimum_points:int=6, maximum_rms_error_px:float=12.0, maximum_error_px:float=30.0)->RegistrationQuality:
    """Assess a thermal→RGB transform against independent/control correspondences."""
    if len(points)<minimum_points:
        return RegistrationQuality(len(points),float('inf'),float('inf'),False,'insufficient_control_points')
    errors=[]
    for p in points:
        x,y=project_homography(matrix,p.thermal_x,p.thermal_y)
        errors.append(sqrt((x-p.rgb_x)**2+(y-p.rgb_y)**2))
    rms=sqrt(sum(v*v for v in errors)/len(errors));mx=max(errors)
    valid=rms<=maximum_rms_error_px and mx<=maximum_error_px
    return RegistrationQuality(len(points),rms,mx,valid,'accepted' if valid else 'reprojection_error_too_high')
