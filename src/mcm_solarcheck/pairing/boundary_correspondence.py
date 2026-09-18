"""Generate fail-closed cross-sensor PV boundary correspondence hypotheses."""
from __future__ import annotations
from dataclasses import dataclass
from .visible_grid_boundary import VisibleBoundary,BoundaryQuality

@dataclass(frozen=True)
class BoundaryCorrespondence:
    thermal:VisibleBoundary
    rgb:VisibleBoundary

def boundary_correspondence_hypotheses(thermal:tuple[BoundaryQuality,...],rgb:tuple[BoundaryQuality,...],axis_mapping:tuple[int,int])->tuple[tuple[BoundaryCorrespondence,...],...]:
    """Return both possible first/last orientations for a known grid-axis mapping.

    Only quality-accepted boundaries participate. Missing evidence is preserved
    by producing partial hypotheses; no correspondence is invented.
    """
    if sorted(axis_mapping)!=[0,1]:raise ValueError('axis_mapping must be a permutation of (0,1)')
    tq=[q.boundary for q in thermal if q.accepted];rq=[q.boundary for q in rgb if q.accepted]
    hypotheses=[]
    for reverse in (False,True):
        pairs=[]
        for t in tq:
            target_family=axis_mapping[t.family_index]
            target_side=('last' if t.side=='first' else 'first') if reverse else t.side
            matches=[r for r in rq if r.family_index==target_family and r.side==target_side]
            if len(matches)==1:pairs.append(BoundaryCorrespondence(t,matches[0]))
        hypotheses.append(tuple(pairs))
    # De-duplicate when sparse evidence makes both orientations identical.
    unique=[]
    for h in hypotheses:
        key=tuple((x.thermal.family_index,x.thermal.side,x.rgb.family_index,x.rgb.side) for x in h)
        if key not in [tuple((x.thermal.family_index,x.thermal.side,x.rgb.family_index,x.rgb.side) for x in u) for u in unique]:unique.append(h)
    return tuple(unique)


@dataclass(frozen=True)
class BoundaryHypothesisScore:
    correspondences:tuple[BoundaryCorrespondence,...]
    rms_error_px:float
    max_error_px:float

def score_boundary_hypothesis(estimate,correspondences:tuple[BoundaryCorrespondence,...])->BoundaryHypothesisScore|None:
    """Score independent boundary endpoints against a fitted grid transform."""
    from math import hypot,sqrt
    from .registration import project_homography
    if not correspondences:return None
    matrix=estimate.estimate.transform.matrix
    if matrix is None:return None
    flat=tuple(v for row in matrix for v in row)
    errors=[]
    for pair in correspondences:
        x,y=project_homography(flat,*pair.thermal.endpoint)
        errors.append(hypot(x-pair.rgb.endpoint[0],y-pair.rgb.endpoint[1]))
    return BoundaryHypothesisScore(correspondences,sqrt(sum(e*e for e in errors)/len(errors)),max(errors))

def filter_estimates_by_boundary_hypotheses(estimates,correspondence_hypotheses:tuple[tuple[BoundaryCorrespondence,...],...],*,minimum_correspondences:int=2,maximum_rms_error_px:float=30.0,maximum_error_px:float=60.0):
    """Keep transforms supported by at least one independent boundary hypothesis."""
    if minimum_correspondences<1:raise ValueError('minimum_correspondences must be positive')
    if maximum_rms_error_px<=0 or maximum_error_px<=0:raise ValueError('boundary error limits must be positive')
    accepted=[]
    for estimate in estimates:
        scores=[score_boundary_hypothesis(estimate,h) for h in correspondence_hypotheses if len(h)>=minimum_correspondences]
        scores=[s for s in scores if s is not None]
        if any(s.rms_error_px<=maximum_rms_error_px and s.max_error_px<=maximum_error_px for s in scores):accepted.append(estimate)
    return tuple(accepted)
