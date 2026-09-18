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


def _signed_axis_rotation(source:float,target:float)->float:
    """Smallest signed rotation between unoriented line axes, in [-90, 90)."""
    return ((target-source+90)%180)-90


def _spacing_profile(lines:tuple[GridLine,...])->tuple[float,...]:
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
                    score=_window_score(tp,_spacing_profile(rgb_lines[ri:ri+count]))
                    candidates.append((score,-count,ti,ri,reversed_order,count))
    candidates.sort()
    best=candidates[0]
    if best[0]>max_spacing_error:return None
    alternatives=[c for c in candidates[1:] if c[5]==best[5]]
    if alternatives and alternatives[0][0]-best[0]<ambiguity_margin:return None
    return GridLineFamilyMatch(thermal,rgb,best[4],best[2],best[3],best[5],best[0])


def _rotation_consistency(thermal:tuple[GridLineFamily,...],rgb:tuple[GridLineFamily,...])->float:
    """Return spread of the common thermal-to-RGB image rotation hypothesis."""
    rotations=[_signed_axis_rotation(t.angle_deg,r.angle_deg) for t,r in zip(thermal,rgb)]
    if len(rotations)<2:return 0.0
    # Rotations are already represented on the same 180-degree axis domain.
    # Pairwise wrapped distance keeps the check stable at the -90/90 boundary.
    errors=[]
    for i in range(len(rotations)):
        for j in range(i+1,len(rotations)):
            errors.append(abs(_signed_axis_rotation(rotations[i],rotations[j])))
    return max(errors) if errors else 0.0


def match_grid_line_families(thermal:tuple[GridLineFamily,...],rgb:tuple[GridLineFamily,...],*,maximum_axis_geometry_error_deg:float=12.0,maximum_absolute_rotation_deg:float=30.0,mapping_ambiguity_margin:float=.03,**kwargs)->tuple[GridLineFamilyMatch,...]:
    """Jointly map PV grid axes using spacing and one common sensor rotation.

    A valid two-axis assignment must permit approximately the same signed image
    rotation for both thermal-to-RGB axes and must remain within a conservative
    absolute rotation envelope. Paired M3T captures share near-simultaneous
    platform geometry, so a near-90-degree axis swap is not a credible sensor
    mapping even when its two rotations are mutually consistent. Ambiguous
    competing mappings still fail closed.
    """
    if maximum_axis_geometry_error_deg<0:raise ValueError('maximum_axis_geometry_error_deg must be non-negative')
    if not 0<=maximum_absolute_rotation_deg<=90:raise ValueError('maximum_absolute_rotation_deg must be between 0 and 90')
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
    selected_t=tuple(thermal[:count])
    candidates=[]
    for r_indices in permutations(range(len(rgb)),count):
        selected_r=tuple(rgb[i] for i in r_indices)
        rotations=tuple(_signed_axis_rotation(t.angle_deg,r.angle_deg) for t,r in zip(selected_t,selected_r))
        if any(abs(rotation)>maximum_absolute_rotation_deg for rotation in rotations):continue
        geometry=_rotation_consistency(selected_t,selected_r)
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
