"""Conservative matching of ordered global PV grid-line families."""
from __future__ import annotations
from dataclasses import dataclass
from math import inf
from statistics import median
from .grid_lines import GridLine,GridLineFamily

@dataclass(frozen=True)
class GridLineFamilyMatch:
    thermal:GridLineFamily
    rgb:GridLineFamily
    reversed_order:bool
    start_thermal:int
    start_rgb:int
    count:int
    score:float


def _spacing_profile(lines:tuple[GridLine,...])->tuple[float,...]:
    """Return direction-independent relative gaps for an explicitly ordered sequence."""
    if len(lines)<2:return ()
    gaps=[abs(lines[i+1].offset_px-lines[i].offset_px) for i in range(len(lines)-1)]
    positive=[gap for gap in gaps if gap>1e-9]
    if len(positive)!=len(gaps):return ()
    scale=median(positive)
    return tuple(round(gap/scale,4) for gap in gaps)


def _window_score(a:tuple[float,...],b:tuple[float,...])->float:
    if len(a)!=len(b) or not a:return inf
    return (sum((x-y)**2 for x,y in zip(a,b))/len(a))**.5


def match_grid_line_family(thermal:GridLineFamily,rgb:GridLineFamily,*,minimum_lines:int=4,max_spacing_error:float=.22,ambiguity_margin:float=.03)->GridLineFamilyMatch|None:
    """Match an ordered contiguous line sequence by relative inter-line spacing."""
    if minimum_lines<3:raise ValueError('minimum_lines must be at least 3')
    if max_spacing_error<=0:raise ValueError('max_spacing_error must be positive')
    if ambiguity_margin<0:raise ValueError('ambiguity_margin must be non-negative')
    n=min(len(thermal.lines),len(rgb.lines))
    if n<minimum_lines:return None
    candidates=[]
    for count in range(n,minimum_lines-1,-1):
        for ti in range(len(thermal.lines)-count+1):
            tp=_spacing_profile(thermal.lines[ti:ti+count])
            for reversed_order in (False,True):
                rgb_lines=tuple(reversed(rgb.lines)) if reversed_order else rgb.lines
                for ri in range(len(rgb_lines)-count+1):
                    rp=_spacing_profile(rgb_lines[ri:ri+count])
                    score=_window_score(tp,rp)
                    candidates.append((score,-count,ti,ri,reversed_order,count))
    candidates.sort()
    best=candidates[0]
    if best[0]>max_spacing_error:return None
    alternatives=[c for c in candidates[1:] if c[5]==best[5]]
    if alternatives and alternatives[0][0]-best[0]<ambiguity_margin:return None
    return GridLineFamilyMatch(thermal,rgb,best[4],best[2],best[3],best[5],best[0])


def match_grid_line_families(thermal:tuple[GridLineFamily,...],rgb:tuple[GridLineFamily,...],**kwargs)->tuple[GridLineFamilyMatch,...]:
    """Choose a one-to-one mapping of up to two approximately orthogonal families."""
    if not thermal or not rgb:return ()
    options=[]
    for ti,t in enumerate(thermal):
        for ri,r in enumerate(rgb):
            match=match_grid_line_family(t,r,**kwargs)
            if match is not None:options.append((match.score,ti,ri,match))
    options.sort(key=lambda item:item[0]);result=[];used_t=set();used_r=set()
    for _,ti,ri,match in options:
        if ti in used_t or ri in used_r:continue
        result.append(match);used_t.add(ti);used_r.add(ri)
    return tuple(result)
