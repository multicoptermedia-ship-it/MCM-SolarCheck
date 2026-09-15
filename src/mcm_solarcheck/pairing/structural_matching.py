"""Conservative matching of RGB/thermal structural points.

The matcher uses modality-independent local geometry. Coordinates are normalized
by image dimensions, while signatures describe sorted distances and neighbour
angles. Mutual-best matching plus an ambiguity margin prevents forced matches.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import atan2,hypot,pi
from .structural_features import StructuralPoint
from .registration import ControlPoint

@dataclass(frozen=True)
class PointSignature:
    point:StructuralPoint
    values:tuple[float,...]

@dataclass(frozen=True)
class StructuralMatch:
    thermal:StructuralPoint
    rgb:StructuralPoint
    score:float


def _normalized(points:tuple[StructuralPoint,...],size:tuple[int,int])->tuple[StructuralPoint,...]:
    w,h=size
    if w<=0 or h<=0:raise ValueError('image dimensions must be positive')
    return tuple(StructuralPoint(p.x/w,p.y/h) for p in points)


def point_signatures(points:tuple[StructuralPoint,...],size:tuple[int,int],*,neighbours:int=5)->tuple[PointSignature,...]:
    if neighbours<2:raise ValueError('neighbours must be at least 2')
    norm=_normalized(points,size);result=[]
    for index,p in enumerate(norm):
        nearby=[]
        for j,q in enumerate(norm):
            if j==index:continue
            dx=q.x-p.x;dy=q.y-p.y;nearby.append((hypot(dx,dy),(atan2(dy,dx)%(2*pi))/(2*pi)))
        nearby.sort(key=lambda item:item[0]);chosen=nearby[:neighbours]
        if len(chosen)<2:continue
        distances=tuple(v[0] for v in chosen);angles=tuple(v[1] for v in chosen)
        # rotation-invariant angular gaps around the point
        ordered=sorted(angles);gaps=tuple(sorted((ordered[(i+1)%len(ordered)]-ordered[i])%1.0 for i in range(len(ordered)))[:neighbours])
        result.append(PointSignature(points[index],distances+gaps))
    return tuple(result)


def _signature_distance(a:PointSignature,b:PointSignature)->float:
    if len(a.values)!=len(b.values):return float('inf')
    return sum((x-y)**2 for x,y in zip(a.values,b.values))**.5


def match_structural_points(thermal_points:tuple[StructuralPoint,...],rgb_points:tuple[StructuralPoint,...],*,thermal_size:tuple[int,int]=(640,512),rgb_size:tuple[int,int]=(4000,3000),neighbours:int=5,max_score:float=.18,ambiguity_margin:float=.025)->tuple[StructuralMatch,...]:
    """Return only mutual, distinctive matches; ambiguous candidates are omitted."""
    ts=point_signatures(thermal_points,thermal_size,neighbours=neighbours);rs=point_signatures(rgb_points,rgb_size,neighbours=neighbours)
    if not ts or not rs:return ()
    distances=[[ _signature_distance(t,r) for r in rs] for t in ts]
    thermal_best=[]
    for row in distances:
        ranked=sorted(range(len(row)),key=row.__getitem__);best=ranked[0];second=row[ranked[1]] if len(ranked)>1 else float('inf')
        thermal_best.append((best,row[best],second))
    rgb_best=[]
    for j in range(len(rs)):
        ranked=sorted(range(len(ts)),key=lambda i:distances[i][j]);best=ranked[0];second=distances[ranked[1]][j] if len(ranked)>1 else float('inf')
        rgb_best.append((best,distances[best][j],second))
    matches=[]
    for i,(j,score,second) in enumerate(thermal_best):
        reverse_i,_,reverse_second=rgb_best[j]
        if reverse_i!=i or score>max_score:continue
        if second-score<ambiguity_margin or reverse_second-score<ambiguity_margin:continue
        matches.append(StructuralMatch(ts[i].point,rs[j].point,score))
    return tuple(sorted(matches,key=lambda m:m.score))


def control_points_from_matches(matches:tuple[StructuralMatch,...])->tuple[ControlPoint,...]:
    return tuple(ControlPoint(m.thermal.x,m.thermal.y,m.rgb.x,m.rgb.y) for m in matches)


def split_fit_holdout(matches:tuple[StructuralMatch,...],*,holdout_fraction:float=.3,minimum_holdout:int=4)->tuple[tuple[ControlPoint,...],tuple[ControlPoint,...]]:
    """Deterministically spatially interleave matches into fit and holdout sets."""
    if not 0<holdout_fraction<1:raise ValueError('holdout_fraction must be between 0 and 1')
    ordered=sorted(matches,key=lambda m:(m.thermal.y,m.thermal.x))
    holdout_count=max(minimum_holdout,round(len(ordered)*holdout_fraction))
    holdout_count=min(holdout_count,max(0,len(ordered)-4))
    if holdout_count<=0:return control_points_from_matches(tuple(ordered)),()
    # Evenly spread holdout samples across the image instead of taking one region.
    holdout_indices={round(i*(len(ordered)-1)/(holdout_count-1)) for i in range(holdout_count)} if holdout_count>1 else {len(ordered)//2}
    fit=[];holdout=[]
    for i,m in enumerate(ordered):
        (holdout if i in holdout_indices else fit).append(m)
    return control_points_from_matches(tuple(fit)),control_points_from_matches(tuple(holdout))
