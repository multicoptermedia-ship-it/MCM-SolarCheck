"""Global PV grid-line families for cross-spectral registration.

Unlike local junction descriptors, this module preserves the ordering and spacing
of repeated near-parallel module-frame lines. Those global relationships are more
useful for matching repetitive PV arrays between M3T thermal and RGB imagery.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import cos,radians,sin
from statistics import median
from .structural_features import StructuralLine,_angle_difference

@dataclass(frozen=True)
class GridLine:
    angle_deg:float
    offset_px:float
    support:int
    length_px:float

@dataclass(frozen=True)
class GridLineFamily:
    angle_deg:float
    lines:tuple[GridLine,...]

    @property
    def spacing_profile(self)->tuple[float,...]:
        if len(self.lines)<2:return ()
        gaps=[self.lines[i+1].offset_px-self.lines[i].offset_px for i in range(len(self.lines)-1)]
        positive=[g for g in gaps if g>1e-9]
        if not positive:return ()
        scale=median(positive)
        return tuple(round(g/scale,4) for g in gaps)


def _mean_axis_angle(lines:tuple[StructuralLine,...])->float:
    # Double angles because unoriented lines repeat every 180 degrees.
    x=sum(cos(radians(2*l.angle_deg))*l.length for l in lines)
    y=sum(sin(radians(2*l.angle_deg))*l.length for l in lines)
    from math import atan2,degrees
    return (degrees(atan2(y,x))/2)%180


def _line_offset(line:StructuralLine,family_angle_deg:float)->float:
    # Signed distance along the family normal, using the segment midpoint.
    mx=(line.x1+line.x2)/2;my=(line.y1+line.y2)/2
    normal=radians(family_angle_deg+90)
    return mx*cos(normal)+my*sin(normal)


def _cluster_offsets(lines:tuple[StructuralLine,...],angle_deg:float,merge_distance_px:float)->tuple[GridLine,...]:
    samples=[(_line_offset(line,angle_deg),index,line) for index,line in enumerate(lines)]
    samples.sort(key=lambda item:(item[0],item[1]))
    groups=[]
    for offset,_,line in samples:
        if not groups or offset-groups[-1][-1][0]>merge_distance_px:groups.append([])
        groups[-1].append((offset,line))
    result=[]
    for group in groups:
        weight=sum(item[1].length for item in group)
        offset=sum(o*l.length for o,l in group)/weight
        result.append(GridLine(angle_deg,offset,len(group),weight))
    return tuple(sorted(result,key=lambda line:line.offset_px))


def _candidate_family(lines:tuple[StructuralLine,...],seed:StructuralLine,angle_tolerance_deg:float,merge_distance_px:float,minimum_lines:int)->GridLineFamily|None:
    members=tuple(line for line in lines if _angle_difference(line.angle_deg,seed.angle_deg)<=angle_tolerance_deg)
    if len(members)<minimum_lines:return None
    angle=_mean_axis_angle(members)
    clustered=_cluster_offsets(members,angle,merge_distance_px)
    if len(clustered)<minimum_lines:return None
    return GridLineFamily(angle,clustered)


def _family_score(family:GridLineFamily)->tuple[int,int,float]:
    """Prefer repeated distinct grid lines over one exceptionally long segment."""
    return (len(family.lines),sum(line.support for line in family.lines),sum(line.length_px for line in family.lines))


def extract_grid_line_families(lines:tuple[StructuralLine,...],*,angle_tolerance_deg:float=12,minimum_family_separation_deg:float=55,merge_distance_px:float=8,minimum_lines:int=3)->tuple[GridLineFamily,...]:
    """Extract at most two dominant, well-separated ordered line families.

    Candidate orientations are evaluated globally. Selection is driven first by
    the number of distinct repeated parallel offsets, then by supporting segments
    and only finally by total length. This prevents a single roof edge or cell
    diagonal from becoming the family seed merely because it is very long.
    """
    if not 0<angle_tolerance_deg<45:raise ValueError('angle_tolerance_deg must be between 0 and 45')
    if not 0<minimum_family_separation_deg<=90:raise ValueError('minimum_family_separation_deg must be between 0 and 90')
    if merge_distance_px<=0:raise ValueError('merge_distance_px must be positive')
    if minimum_lines<2:raise ValueError('minimum_lines must be at least 2')
    if not lines:return ()
    candidates=[]
    for seed in lines:
        family=_candidate_family(lines,seed,angle_tolerance_deg,merge_distance_px,minimum_lines)
        if family is None:continue
        if any(_angle_difference(family.angle_deg,existing.angle_deg)<1 for existing in candidates):continue
        candidates.append(family)
    candidates.sort(key=_family_score,reverse=True)
    selected=[]
    for family in candidates:
        if all(_angle_difference(family.angle_deg,other.angle_deg)>=minimum_family_separation_deg for other in selected):
            selected.append(family)
            if len(selected)==2:break
    return tuple(selected)
