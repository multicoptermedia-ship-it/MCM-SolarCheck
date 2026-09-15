"""PV-grid topology descriptors for cross-spectral registration.

A junction is described by neighbour occupancy and relative spacing along its two
local structural axes. This is more selective than treating intersections as
independent points and remains independent of RGB/thermal appearance.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import cos,sin,radians,hypot
from .oriented_features import OrientedStructuralPoint

@dataclass(frozen=True)
class GridTopologySignature:
    point:OrientedStructuralPoint
    axis_profiles:tuple[tuple[float,...],tuple[float,...]]
    occupancy:tuple[int,int]


def _axis_profile(point:OrientedStructuralPoint,points:tuple[OrientedStructuralPoint,...],angle_deg:float,size:tuple[int,int],*,angular_tolerance_deg:float=18,max_neighbours_per_side:int=2)->tuple[tuple[float,...],int]:
    w,h=size;ux=cos(radians(angle_deg));uy=sin(radians(angle_deg));along_pos=[];along_neg=[]
    # Work in normalized image coordinates so sensor resolution does not dominate.
    for q in points:
        if q is point:continue
        dx=(q.x-point.x)/w;dy=(q.y-point.y)/h
        along=dx*ux+dy*uy;perp=abs(-dx*uy+dy*ux)
        if abs(along)<1e-9:continue
        # tan(tolerance) without importing another function; ratio is sufficient.
        if perp/abs(along)>.325:continue
        (along_pos if along>0 else along_neg).append(abs(along))
    along_pos.sort();along_neg.sort();chosen=along_neg[:max_neighbours_per_side]+along_pos[:max_neighbours_per_side]
    if not chosen:return (),0
    scale=min(chosen);profile=tuple(sorted(round(v/scale,4) for v in chosen))
    occupancy=(1 if along_neg else 0)+(1 if along_pos else 0)
    return profile,occupancy


def grid_topology_signatures(points:tuple[OrientedStructuralPoint,...],size:tuple[int,int])->tuple[GridTopologySignature,...]:
    if size[0]<=0 or size[1]<=0:raise ValueError('image dimensions must be positive')
    result=[]
    for p in points:
        pa,oa=_axis_profile(p,points,p.angle_a_deg,size);pb,ob=_axis_profile(p,points,p.angle_b_deg,size)
        # Axis order is arbitrary across modalities. Canonicalize by profile then occupancy.
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
