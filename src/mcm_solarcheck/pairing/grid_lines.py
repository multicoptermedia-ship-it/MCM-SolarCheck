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
    samples=sorted((_line_offset(line,angle_deg),line) for line in lines)
    groups=[]
    for offset,line in samples:
        if not groups or offset-groups[-1][-1][0]>merge_distance_px:groups.append([])
        groups[-1].append((offset,line))
    result=[]
    for group in groups:
        weight=sum(item[1].length for item in group)
        offset=sum(o*l.length for o,l in group)/weight
        result.append(GridLine(angle_deg,offset,len(group),weight))
    return tuple(sorted(result,key=lambda line:line.offset_px))


def extract_grid_line_families(lines:tuple[StructuralLine,...],*,angle_tolerance_deg:float=12,minimum_family_separation_deg:float=55,merge_distance_px:float=8,minimum_lines:int=3)->tuple[GridLineFamily,...]:
    """Extract at most two dominant, well-separated ordered line families."""
    if not 0<angle_tolerance_deg<45:raise ValueError('angle_tolerance_deg must be between 0 and 45')
    if merge_distance_px<=0:raise ValueError('merge_distance_px must be positive')
    if minimum_lines<2:raise ValueError('minimum_lines must be at least 2')
    if not lines:return ()
    candidates=sorted(lines,key=lambda line:line.length,reverse=True)
    families=[];used=set()
    while len(families)<2:
        seed=next((line for line in candidates if id(line) not in used and all(_angle_difference(line.angle_deg,f.angle_deg)>=minimum_family_separation_deg for f in families)),None)
        if seed is None:break
        members=tuple(line for line in lines if _angle_difference(line.angle_deg,seed.angle_deg)<=angle_tolerance_deg)
        used.update(id(line) for line in members)
        if len(members)<minimum_lines:continue
        angle=_mean_axis_angle(members)
        clustered=_cluster_offsets(members,angle,merge_distance_px)
        if len(clustered)>=minimum_lines:families.append(GridLineFamily(angle,clustered))
    return tuple(families)
