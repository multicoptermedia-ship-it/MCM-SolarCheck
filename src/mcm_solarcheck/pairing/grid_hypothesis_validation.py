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


def select_unique_grid_hypothesis(estimates:tuple[GridHypothesisEstimate,...],*,minimum_control_point_advantage:int=4,minimum_rms_ratio:float=1.5)->GridHypothesisEstimate|None:
    """Accept one 2-D hypothesis only when it is clearly better than alternatives.

    Regular PV grids can support many low-error homographies with different
    physical line identities.  Prefer broader evidence first, then require a
    substantial RMS advantage over an equally supported competitor.  Exact or
    near-equivalent alternatives fail closed.
    """
    if minimum_control_point_advantage<1:raise ValueError('minimum_control_point_advantage must be positive')
    if minimum_rms_ratio<=1:raise ValueError('minimum_rms_ratio must be greater than 1')
    if not estimates:return None
    ranked=sorted(estimates,key=lambda e:(-e.estimate.quality.control_points,e.estimate.quality.rms_error_px,e.estimate.quality.max_error_px))
    best=ranked[0]
    if len(ranked)==1:return best
    second=ranked[1]
    bp=best.estimate.quality.control_points;sp=second.estimate.quality.control_points
    if bp-sp>=minimum_control_point_advantage:return best
    # When evidence coverage is comparable, error alone is accepted only with
    # a material separation; tiny numerical differences on repetitive grids
    # are not physical identity evidence.
    br=best.estimate.quality.rms_error_px;sr=second.estimate.quality.rms_error_px
    if br<=1e-12:return best if sr>1e-9 else None
    return best if sr/br>=minimum_rms_ratio else None
