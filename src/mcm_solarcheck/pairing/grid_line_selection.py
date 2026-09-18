"""Cross-resolution selection of repeated PV grid lines.

RGB imagery can expose many more parallel edges than the thermal image.  This
module selects a regular, strongly supported subsequence without changing the
registration acceptance thresholds.  Selection is deliberately fail-closed when
two competing subsequences are statistically indistinguishable.
"""
from __future__ import annotations
from dataclasses import dataclass
from statistics import median
from .grid_lines import GridLine,GridLineFamily

@dataclass(frozen=True)
class GridLineSelection:
    family:GridLineFamily
    start:int
    step:int
    count:int
    regularity_error:float
    support_score:float


def _regularity(lines:tuple[GridLine,...])->float:
    if len(lines)<3:return float('inf')
    gaps=[abs(lines[i+1].offset_px-lines[i].offset_px) for i in range(len(lines)-1)]
    scale=median(gaps)
    if scale<=1e-9:return float('inf')
    return (sum(((gap/scale)-1.0)**2 for gap in gaps)/len(gaps))**.5


def select_regular_grid_lines(family:GridLineFamily,*,minimum_lines:int=4,maximum_regularity_error:float=.18,ambiguity_margin:float=.02)->GridLineSelection|None:
    """Select one regular ordered subsequence from an over-detected family.

    Candidate strides allow RGB cell/frame edges to collapse to the coarser
    module-grid cadence visible in thermal imagery.  More retained lines are
    preferred first; regularity and normalized support then break ties.  A
    near-equal competing candidate fails closed.
    """
    if minimum_lines<3:raise ValueError('minimum_lines must be at least 3')
    if maximum_regularity_error<=0:raise ValueError('maximum_regularity_error must be positive')
    if ambiguity_margin<0:raise ValueError('ambiguity_margin must be non-negative')
    lines=family.lines
    if len(lines)<minimum_lines:return None
    candidates=[]
    max_step=max(1,len(lines)//minimum_lines)
    for step in range(1,max_step+1):
        for start in range(step):
            selected=lines[start::step]
            if len(selected)<minimum_lines:continue
            error=_regularity(selected)
            if error>maximum_regularity_error:continue
            support=sum(line.support for line in selected)/len(selected)
            candidates.append((-len(selected),error,-support,start,step,selected))
    if not candidates:return None
    candidates.sort(key=lambda item:item[:5])
    best=candidates[0]
    # Ambiguity is meaningful only between candidates retaining the same number
    # of lines; a denser valid grid is intentionally preferred.
    peers=[candidate for candidate in candidates[1:] if candidate[0]==best[0]]
    if peers and abs(peers[0][1]-best[1])<ambiguity_margin and abs(peers[0][2]-best[2])<1e-9:return None
    selected=tuple(best[5])
    return GridLineSelection(GridLineFamily(family.angle_deg,selected),best[3],best[4],len(selected),best[1],-best[2])
