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
