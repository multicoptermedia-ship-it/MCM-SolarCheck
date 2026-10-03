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


@dataclass(frozen=True)
class CrossResolutionGridSelection:
    thermal:GridLineFamily
    rgb:GridLineFamily
    thermal_step:int
    rgb_step:int
    count:int
    spacing_error:float
    reversed_order:bool


def _profile(lines:tuple[GridLine,...])->tuple[float,...]:
    if len(lines)<2:return ()
    gaps=[abs(lines[i+1].offset_px-lines[i].offset_px) for i in range(len(lines)-1)]
    scale=median(gaps)
    if scale<=1e-9:return ()
    return tuple(gap/scale for gap in gaps)


def _profile_error(a:tuple[float,...],b:tuple[float,...])->float:
    if len(a)!=len(b) or not a:return float('inf')
    return (sum((x-y)**2 for x,y in zip(a,b))/len(a))**.5


def match_cross_resolution_grid_lines(thermal:GridLineFamily,rgb:GridLineFamily,*,minimum_lines:int=4,max_spacing_error:float=.18,ambiguity_margin:float=.02,max_step:int=12)->CrossResolutionGridSelection|None:
    """Jointly select comparable thermal/RGB grid cadences.

    Unlike single-family regularity selection, this routine uses cross-sensor
    spacing evidence before deciding whether dense RGB edges should be skipped.
    It never fabricates correspondences: competing candidates within the
    ambiguity margin are refused.
    """
    if minimum_lines<3:raise ValueError('minimum_lines must be at least 3')
    if max_spacing_error<=0:raise ValueError('max_spacing_error must be positive')
    if ambiguity_margin<0:raise ValueError('ambiguity_margin must be non-negative')
    if max_step<1:raise ValueError('max_step must be positive')
    candidates=[]
    # A stride may still leave minimum_lines when the selected phase starts
    # early enough. floor(len/minimum_lines) incorrectly excludes such valid
    # cadences (e.g. 8 RGB lines, stride 2 -> 4 lines).
    tmax=min(max_step,max(1,(len(thermal.lines)-1)//(minimum_lines-1)))
    rmax=min(max_step,max(1,(len(rgb.lines)-1)//(minimum_lines-1)))
    for ts in range(1,tmax+1):
        for ti in range(ts):
            ta=thermal.lines[ti::ts]
            for rs in range(1,rmax+1):
                for ri in range(rs):
                    rb=rgb.lines[ri::rs]
                    n=min(len(ta),len(rb))
                    for count in range(n,minimum_lines-1,-1):
                        for tw in range(len(ta)-count+1):
                            tl=ta[tw:tw+count];tp=_profile(tl)
                            for reversed_order in (False,True):
                                ordered=tuple(reversed(rb)) if reversed_order else rb
                                for rw in range(len(ordered)-count+1):
                                    rl=ordered[rw:rw+count]
                                    error=_profile_error(tp,_profile(rl))
                                    if error<=max_spacing_error:
                                        # Prefer more evidence, then simpler cadence,
                                        # then spacing agreement.
                                        candidates.append((-count,ts+rs,error,ts,rs,ti,ri,tw,rw,reversed_order,tl,rl))
    if not candidates:return None
    candidates.sort(key=lambda item:item[:10])
    best=candidates[0]
    # With a zero ambiguity margin the caller explicitly requests a deterministic
    # best candidate. Strict fail-closed ambiguity applies only for a positive
    # margin; exact ties are then rejected as intended.
    peers=[c for c in candidates[1:] if c[0]==best[0] and c[1]==best[1]]
    if ambiguity_margin>0 and peers and peers[0][2]-best[2]<ambiguity_margin:return None
    return CrossResolutionGridSelection(
        GridLineFamily(thermal.angle_deg,tuple(best[10])),
        GridLineFamily(rgb.angle_deg,tuple(best[11])),
        best[3],best[4],-best[0],best[2],best[9])


def cross_resolution_grid_candidates(thermal:GridLineFamily,rgb:GridLineFamily,*,minimum_lines:int=4,max_spacing_error:float=.18,max_step:int=12)->tuple[CrossResolutionGridSelection,...]:
    """Return all admissible cadence/phase hypotheses for later 2-D validation.

    This deliberately does not choose a winner.  Spacing is only a proposal
    stage; direction, phase and line identity must be resolved by joint
    two-axis geometry plus independent registration holdout.
    """
    if minimum_lines<3:raise ValueError('minimum_lines must be at least 3')
    if max_spacing_error<=0:raise ValueError('max_spacing_error must be positive')
    if max_step<1:raise ValueError('max_step must be positive')
    candidates=[]
    tmax=min(max_step,max(1,(len(thermal.lines)-1)//(minimum_lines-1)))
    rmax=min(max_step,max(1,(len(rgb.lines)-1)//(minimum_lines-1)))
    for ts in range(1,tmax+1):
        for ti in range(ts):
            ta=thermal.lines[ti::ts]
            for rs in range(1,rmax+1):
                for ri in range(rs):
                    rb=rgb.lines[ri::rs]
                    n=min(len(ta),len(rb))
                    for count in range(n,minimum_lines-1,-1):
                        for tw in range(len(ta)-count+1):
                            tl=ta[tw:tw+count];tp=_profile(tl)
                            for reversed_order in (False,True):
                                ordered=tuple(reversed(rb)) if reversed_order else rb
                                for rw in range(len(ordered)-count+1):
                                    rl=ordered[rw:rw+count]
                                    error=_profile_error(tp,_profile(rl))
                                    if error<=max_spacing_error:
                                        candidates.append(CrossResolutionGridSelection(
                                            GridLineFamily(thermal.angle_deg,tuple(tl)),
                                            GridLineFamily(rgb.angle_deg,tuple(rl)),
                                            ts,rs,count,error,reversed_order))
    candidates.sort(key=lambda x:(-x.count,x.thermal_step+x.rgb_step,x.spacing_error,x.thermal_step,x.rgb_step,x.reversed_order))
    return tuple(candidates)
