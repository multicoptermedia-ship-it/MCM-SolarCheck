"""Conservative matching of ordered global PV grid-line families."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import permutations
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


def _axis_difference(a:float,b:float)->float:
    d=abs(a-b)%180
    return min(d,180-d)


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


def _mapping_geometry_score(thermal:tuple[GridLineFamily,...],rgb:tuple[GridLineFamily,...],mapping:tuple[int,...])->float:
    """Compare relative axis geometry without assuming equal absolute image rotation."""
    if len(mapping)<2:return 0.0
    errors=[]
    for i in range(len(mapping)):
        for j in range(i+1,len(mapping)):
            thermal_cross=_axis_difference(thermal[i].angle_deg,thermal[j].angle_deg)
            rgb_cross=_axis_difference(rgb[mapping[i]].angle_deg,rgb[mapping[j]].angle_deg)
            errors.append(abs(thermal_cross-rgb_cross))
    return sum(errors)/len(errors) if errors else 0.0


def match_grid_line_families(thermal:tuple[GridLineFamily,...],rgb:tuple[GridLineFamily,...],*,maximum_axis_geometry_error_deg:float=12.0,mapping_ambiguity_margin:float=.03,**kwargs)->tuple[GridLineFamilyMatch,...]:
    """Jointly choose the cross-sensor mapping of the two PV grid axes.

    Absolute RGB and thermal angles may differ because the sensors have different
    image geometry, so individual axes are not required to have the same angle.
    The crossing angle between the two axes must however remain geometrically
    plausible. Competing permutations are evaluated as a pair and ambiguous
    mappings fail closed instead of greedily accepting a spacing look-alike.
    """
    if maximum_axis_geometry_error_deg<0:raise ValueError('maximum_axis_geometry_error_deg must be non-negative')
    if mapping_ambiguity_margin<0:raise ValueError('mapping_ambiguity_margin must be non-negative')
    if not thermal or not rgb:return ()
    count=min(len(thermal),len(rgb),2)
    if count<2:
        options=[]
        for ti,t in enumerate(thermal):
            for ri,r in enumerate(rgb):
                match=match_grid_line_family(t,r,**kwargs)
                if match is not None:options.append((match.score,ti,ri,match))
        options.sort(key=lambda item:item[0])
        return (options[0][3],) if options else ()
    candidates=[]
    for t_indices in permutations(range(len(thermal)),count):
        if tuple(sorted(t_indices))!=tuple(range(count)):continue
        selected_t=tuple(thermal[i] for i in t_indices)
        for r_indices in permutations(range(len(rgb)),count):
            selected_r=tuple(rgb[i] for i in r_indices)
            geometry=_mapping_geometry_score(selected_t,rgb,r_indices)
            if geometry>maximum_axis_geometry_error_deg:continue
            matches=[]
            for t,r in zip(selected_t,selected_r):
                match=match_grid_line_family(t,r,**kwargs)
                if match is None:break
                matches.append(match)
            if len(matches)!=count:continue
            spacing=sum(m.score for m in matches)/count
            candidates.append((spacing,geometry,tuple(r_indices),tuple(matches)))
    if not candidates:return ()
    candidates.sort(key=lambda item:(item[0],item[1],item[2]))
    best=candidates[0]
    if len(candidates)>1 and candidates[1][0]-best[0]<mapping_ambiguity_margin:return ()
    return best[3]
