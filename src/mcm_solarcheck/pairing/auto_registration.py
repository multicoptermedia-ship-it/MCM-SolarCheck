"""Fail-closed automatic thermal-to-RGB structural registration."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .geometry import PixelTransform
from .registration import HomographyEstimate,RegistrationQuality,estimate_homography
from .structural_features import detect_structural_lines
from .oriented_features import oriented_intersections
from .oriented_matching import match_oriented_points,split_oriented_matches

@dataclass(frozen=True)
class AutoRegistrationResult:
    estimate:HomographyEstimate
    thermal_points:int
    rgb_points:int
    matches:int
    status:str


def _refused(thermal_size:tuple[int,int],rgb_size:tuple[int,int],matches:int,status:str)->HomographyEstimate:
    q=RegistrationQuality(0,float('inf'),float('inf'),False,status)
    return HomographyEstimate(PixelTransform('oriented_structural_homography',False,*thermal_size,*rgb_size),q,matches,0)


def register_structural_images(thermal_image:np.ndarray,rgb_image:np.ndarray,*,minimum_matches:int=10,minimum_fit_points:int=6,minimum_validation_points:int=4,max_score:float=.2,ambiguity_margin:float=.025,maximum_crossing_angle_delta_deg:float=12)->AutoRegistrationResult:
    """Detect oriented grid junctions, match, fit and independently validate."""
    if minimum_matches<minimum_fit_points+minimum_validation_points:raise ValueError('minimum_matches must cover fit and validation requirements')
    th,tw=thermal_image.shape[:2];rh,rw=rgb_image.shape[:2]
    thermal_size=(tw,th);rgb_size=(rw,rh)
    tl=detect_structural_lines(thermal_image);rl=detect_structural_lines(rgb_image)
    tp=oriented_intersections(tl,tw,th);rp=oriented_intersections(rl,rw,rh)
    matches=match_oriented_points(tp,rp,thermal_size=thermal_size,rgb_size=rgb_size,max_score=max_score,ambiguity_margin=ambiguity_margin,maximum_crossing_angle_delta_deg=maximum_crossing_angle_delta_deg)
    if len(matches)<minimum_matches:
        estimate=_refused(thermal_size,rgb_size,len(matches),'insufficient_oriented_structural_matches')
        return AutoRegistrationResult(estimate,len(tp),len(rp),len(matches),'insufficient_oriented_structural_matches')
    fit,holdout=split_oriented_matches(matches,minimum_holdout=minimum_validation_points)
    estimate=estimate_homography(fit,holdout,thermal_size=thermal_size,rgb_size=rgb_size,minimum_fit_points=minimum_fit_points,minimum_validation_points=minimum_validation_points)
    status='validated' if estimate.transform.validated else estimate.quality.reason
    return AutoRegistrationResult(estimate,len(tp),len(rp),len(matches),status)
