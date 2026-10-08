"""Reproducible diagnostics for real M3T thermal/RGB registration datasets.

This module intentionally contains no dataset-specific thresholds. It records the
intermediate evidence used by the production global-grid pipeline so development
and final acceptance runs can be compared without weakening fail-closed gates.
"""
from __future__ import annotations
from dataclasses import asdict,dataclass
import json
from pathlib import Path
import cv2
from .structural_features import detect_structural_lines
from .grid_lines import extract_grid_line_families
from .grid_line_matching import match_grid_line_families
from .grid_control_points import grid_control_points,split_grid_control_points
from .registration import estimate_homography

@dataclass(frozen=True)
class FamilyDiagnostic:
    angle_deg:float
    lines:int
    offsets_px:tuple[float,...]

@dataclass(frozen=True)
class FamilyMatchDiagnostic:
    thermal_angle_deg:float
    rgb_angle_deg:float
    rotation_deg:float
    reversed_order:bool
    count:int
    score:float

@dataclass(frozen=True)
class RegistrationDiagnostic:
    thermal_file:str
    rgb_file:str
    thermal_lines:int
    rgb_lines:int
    thermal_families:tuple[FamilyDiagnostic,...]
    rgb_families:tuple[FamilyDiagnostic,...]
    family_matches:tuple[FamilyMatchDiagnostic,...]
    control_points:int
    fit_points:int
    holdout_points:int
    inliers:int
    rms_error_px:float
    max_error_px:float
    validated:bool
    status:str


def _rotation(source:float,target:float)->float:
    return ((target-source+90)%180)-90


def _family(family)->FamilyDiagnostic:
    return FamilyDiagnostic(family.angle_deg,len(family.lines),tuple(line.offset_px for line in family.lines))


def validate_pair(thermal_path:str|Path,rgb_path:str|Path,*,minimum_fit_points:int=6,minimum_validation_points:int=4,minimum_family_lines:int=4,max_spacing_error:float=.22,ambiguity_margin:float=.03)->RegistrationDiagnostic:
    thermal_path=Path(thermal_path);rgb_path=Path(rgb_path)
    thermal=cv2.imread(str(thermal_path),cv2.IMREAD_COLOR);rgb=cv2.imread(str(rgb_path),cv2.IMREAD_COLOR)
    if thermal is None:raise ValueError(f'cannot read thermal image: {thermal_path}')
    if rgb is None:raise ValueError(f'cannot read RGB image: {rgb_path}')
    tl=detect_structural_lines(thermal);rl=detect_structural_lines(rgb)
    tf=extract_grid_line_families(tl,minimum_lines=minimum_family_lines)
    rf=extract_grid_line_families(rl,minimum_lines=minimum_family_lines)
    matches=match_grid_line_families(tf,rf,minimum_lines=minimum_family_lines,max_spacing_error=max_spacing_error,ambiguity_margin=ambiguity_margin)
    md=tuple(FamilyMatchDiagnostic(m.thermal.angle_deg,m.rgb.angle_deg,_rotation(m.thermal.angle_deg,m.rgb.angle_deg),m.reversed_order,m.count,m.score) for m in matches)
    base=dict(thermal_file=thermal_path.name,rgb_file=rgb_path.name,thermal_lines=len(tl),rgb_lines=len(rl),thermal_families=tuple(_family(f) for f in tf),rgb_families=tuple(_family(f) for f in rf),family_matches=md)
    if len(matches)!=2:return RegistrationDiagnostic(**base,control_points=0,fit_points=0,holdout_points=0,inliers=0,rms_error_px=float('inf'),max_error_px=float('inf'),validated=False,status='insufficient_global_grid_family_matches')
    points=grid_control_points(matches);required=minimum_fit_points+minimum_validation_points
    if len(points)<required:return RegistrationDiagnostic(**base,control_points=len(points),fit_points=0,holdout_points=0,inliers=0,rms_error_px=float('inf'),max_error_px=float('inf'),validated=False,status='insufficient_global_grid_control_points')
    fit,holdout=split_grid_control_points(points,minimum_fit=minimum_fit_points,minimum_holdout=minimum_validation_points)
    if len(fit)<minimum_fit_points or len(holdout)<minimum_validation_points:return RegistrationDiagnostic(**base,control_points=len(points),fit_points=len(fit),holdout_points=len(holdout),inliers=0,rms_error_px=float('inf'),max_error_px=float('inf'),validated=False,status='insufficient_global_grid_holdout')
    th,tw=thermal.shape[:2];rh,rw=rgb.shape[:2]
    estimate=estimate_homography(fit,holdout,thermal_size=(tw,th),rgb_size=(rw,rh),minimum_fit_points=minimum_fit_points,minimum_validation_points=minimum_validation_points)
    status='validated' if estimate.transform.validated else estimate.quality.reason
    return RegistrationDiagnostic(**base,control_points=len(points),fit_points=len(fit),holdout_points=len(holdout),inliers=estimate.inliers,rms_error_px=estimate.quality.rms_error_px,max_error_px=estimate.quality.max_error_px,validated=estimate.transform.validated,status=status)


def validate_pairs(pairs,output_path:str|Path|None=None)->tuple[RegistrationDiagnostic,...]:
    results=tuple(validate_pair(thermal,rgb) for thermal,rgb in pairs)
    if output_path is not None:
        Path(output_path).write_text(json.dumps([asdict(result) for result in results],indent=2,allow_nan=True),encoding='utf-8')
    return results
