"""Joint 2-D validation of cross-resolution PV grid hypotheses."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from .grid_line_selection import CrossResolutionGridSelection
from .grid_line_matching import GridLineFamilyMatch
from .grid_control_points import grid_control_points,split_grid_control_points
from .registration import HomographyEstimate,estimate_homography

@dataclass(frozen=True)
class GridHypothesisEstimate:
    first:CrossResolutionGridSelection
    second:CrossResolutionGridSelection
    estimate:HomographyEstimate

def _as_match(selection:CrossResolutionGridSelection)->GridLineFamilyMatch:
    # Selected families already contain the exact cadence/window and RGB order.
    return GridLineFamilyMatch(selection.thermal,selection.rgb,False,0,0,selection.count,selection.spacing_error)

def validate_grid_hypotheses(first:tuple[CrossResolutionGridSelection,...],second:tuple[CrossResolutionGridSelection,...],*,minimum_fit:int=6,minimum_holdout:int=4,maximum_rms_error_px:float=12.0,maximum_error_px:float=30.0)->tuple[GridHypothesisEstimate,...]:
    """Return only hypotheses that survive independent 2-D holdout validation.

    Spacing proposes candidates; it never decides physical line identity.
    Every cross-axis combination must independently pass the same registration
    quality gates used by production homography estimation.
    """
    accepted=[]
    for a,b in product(first,second):
        points=grid_control_points((_as_match(a),_as_match(b)))
        fit,holdout=split_grid_control_points(points,minimum_fit=minimum_fit,minimum_holdout=minimum_holdout)
        if not fit or not holdout:continue
        estimate=estimate_homography(fit,holdout,minimum_fit_points=minimum_fit,minimum_validation_points=minimum_holdout,maximum_rms_error_px=maximum_rms_error_px,maximum_error_px=maximum_error_px)
        if estimate.quality.validated:
            accepted.append(GridHypothesisEstimate(a,b,estimate))
    return tuple(accepted)
