"""PV-grid topology descriptors for cross-spectral registration.

A junction is described by neighbour occupancy and relative spacing along its two
local structural axes. Projection is performed in native pixel geometry; spacing
ratios then remove uniform sensor scale without mixing normalized axes with
pixel-space line angles.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import cos,sin,radians,tan
from statistics import median
from .oriented_features import OrientedStructuralPoint

@dataclass(frozen=True)
class GridTopologySignature:
    point:OrientedStructuralPoint
    axis_profiles:tuple[tuple[float,...],tuple[float,...]]
    occupancy:tuple[int,int]


def _axis_profile(point:OrientedStructuralPoint,points:tuple[OrientedStructuralPoint,...],angle_deg:float,*,angular_tolerance_deg:float=18,max_neighbours_per_side:int=2)->tuple[tuple[float,...],int]:
    if not 0<angular_tolerance_deg<90:raise ValueError('angular_tolerance_deg must be between 0 and 90')
    if max_neighbours_per_side<1:raise ValueError('max_neighbours_per_side must be positive')
    ux=cos(radians(angle_deg));uy=sin(radians(angle_deg));limit=tan(radians(angular_tolerance_deg));along_pos=[];along_neg=[]
    for q in points:
        if q is point:continue
        dx=q.x-point.x;dy=q.y-point.y
        along=dx*ux+dy*uy;perp=abs(-dx*uy+dy*ux)
        if abs(along)<1e-9 or perp/abs(along)>limit:continue
        (along_pos if along>0 else along_neg).append(abs(along))
    along_pos.sort();along_neg.sort();chosen=along_neg[:max_neighbours_per_side]+along_pos[:max_neighbours_per_side]
    if not chosen:return (),0
    # A median local spacing is less sensitive than the nearest point to a spurious
    # duplicate intersection while retaining scale invariance across sensors.
    nearest=[]
    if along_neg:nearest.append(along_neg[0])
    if along_pos:nearest.append(along_pos[0])
    scale=median(nearest) if nearest else median(chosen)
    profile=tuple(sorted(round(v/scale,4) for v in chosen))
    occupancy=(1 if along_neg else 0)+(1 if along_pos else 0)
    return profile,occupancy


def grid_topology_signatures(points:tuple[OrientedStructuralPoint,...],size:tuple[int,int],*,angular_tolerance_deg:float=18,max_neighbours_per_side:int=2)->tuple[GridTopologySignature,...]:
    if size[0]<=0 or size[1]<=0:raise ValueError('image dimensions must be positive')
    result=[]
    for p in points:
        pa,oa=_axis_profile(p,points,p.angle_a_deg,angular_tolerance_deg=angular_tolerance_deg,max_neighbours_per_side=max_neighbours_per_side)
        pb,ob=_axis_profile(p,points,p.angle_b_deg,angular_tolerance_deg=angular_tolerance_deg,max_neighbours_per_side=max_neighbours_per_side)
        axes=sorted(((pa,oa),(pb,ob)),key=lambda item:(item[1],item[0]))
        result.append(GridTopologySignature(p,(axes[0][0],axes[1][0]),(axes[0][1],axes[1][1])))
    return tuple(result)


def topology_distance(a:GridTopologySignature,b:GridTopologySignature)->float:
    if a.occupancy!=b.occupancy:return float('inf')
    total=0.0;count=0
    for left,right in zip(a.axis_profiles,b.axis_profiles):
        if len(left)!=len(right):return float('inf')
        for x,y in zip(left,right):total+=(x-y)**2;count+=1
    return (total/max(1,count))**.5
