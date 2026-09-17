"""Fail-closed automatic thermal-to-RGB structural registration."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .geometry import PixelTransform
from .registration import HomographyEstimate,RegistrationQuality,estimate_homography
from .structural_features import detect_structural_lines
from .oriented_features import oriented_intersections
from .oriented_matching import match_oriented_points,split_oriented_matches
from .grid_lines import extract_grid_line_families
from .grid_line_matching import match_grid_line_families
from .grid_control_points import grid_control_points,split_grid_control_points

@dataclass(frozen=True)
class AutoRegistrationResult:
    estimate:HomographyEstimate
    thermal_points:int
    rgb_points:int
    matches:int
    status:str


def _refused(thermal_size:tuple[int,int],rgb_size:tuple[int,int],matches:int,status:str,method:str='oriented_structural_homography')->HomographyEstimate:
    q=RegistrationQuality(0,float('inf'),float('inf'),False,status)
    # A refused registration has not fitted any points. `matches` is diagnostic
    # evidence only and must not be reported as fit_points.
    return HomographyEstimate(PixelTransform(method,False,*thermal_size,*rgb_size),q,0,0)


def register_global_grid_images(thermal_image:np.ndarray,rgb_image:np.ndarray,*,minimum_fit_points:int=6,minimum_validation_points:int=4,minimum_family_lines:int=4,max_spacing_error:float=.22,ambiguity_margin:float=.03)->AutoRegistrationResult:
    """Register using ordered global PV grid families and independent holdout points."""
    if minimum_fit_points<4:raise ValueError('minimum_fit_points must be at least 4')
    if minimum_validation_points<4:raise ValueError('minimum_validation_points must be at least 4')
    th,tw=thermal_image.shape[:2];rh,rw=rgb_image.shape[:2]
    thermal_size=(tw,th);rgb_size=(rw,rh)
    tl=detect_structural_lines(thermal_image);rl=detect_structural_lines(rgb_image)
    tf=extract_grid_line_families(tl,minimum_lines=minimum_family_lines)
    rf=extract_grid_line_families(rl,minimum_lines=minimum_family_lines)
    family_matches=match_grid_line_families(tf,rf,minimum_lines=minimum_family_lines,max_spacing_error=max_spacing_error,ambiguity_margin=ambiguity_margin)
    if len(family_matches)!=2:
        estimate=_refused(thermal_size,rgb_size,len(family_matches),'insufficient_global_grid_family_matches','global_grid_homography')
        return AutoRegistrationResult(estimate,sum(len(f.lines) for f in tf),sum(len(f.lines) for f in rf),len(family_matches),'insufficient_global_grid_family_matches')
    points=grid_control_points(family_matches)
    required=minimum_fit_points+minimum_validation_points
    if len(points)<required:
        estimate=_refused(thermal_size,rgb_size,len(points),'insufficient_global_grid_control_points','global_grid_homography')
        return AutoRegistrationResult(estimate,sum(len(f.lines) for f in tf),sum(len(f.lines) for f in rf),len(points),'insufficient_global_grid_control_points')
    fit,holdout=split_grid_control_points(points,minimum_fit=minimum_fit_points,minimum_holdout=minimum_validation_points)
    if len(fit)<minimum_fit_points or len(holdout)<minimum_validation_points:
        estimate=_refused(thermal_size,rgb_size,len(points),'insufficient_global_grid_holdout','global_grid_homography')
        return AutoRegistrationResult(estimate,sum(len(f.lines) for f in tf),sum(len(f.lines) for f in rf),len(points),'insufficient_global_grid_holdout')
    estimate=estimate_homography(fit,holdout,thermal_size=thermal_size,rgb_size=rgb_size,minimum_fit_points=minimum_fit_points,minimum_validation_points=minimum_validation_points)
    status='validated' if estimate.transform.validated else estimate.quality.reason
    return AutoRegistrationResult(estimate,sum(len(f.lines) for f in tf),sum(len(f.lines) for f in rf),len(points),status)


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
