"""Orientation- and topology-aware matching of thermal and RGB PV-grid intersections."""
from __future__ import annotations
from dataclasses import dataclass
from math import atan2,hypot,pi
from .oriented_features import OrientedStructuralPoint
from .grid_topology import grid_topology_signatures,topology_distance
from .registration import ControlPoint

@dataclass(frozen=True)
class OrientedSignature:
    point:OrientedStructuralPoint
    values:tuple[float,...]

@dataclass(frozen=True)
class OrientedMatch:
    thermal:OrientedStructuralPoint
    rgb:OrientedStructuralPoint
    score:float


def oriented_signatures(points:tuple[OrientedStructuralPoint,...],size:tuple[int,int],*,neighbours:int=5,angle_weight:float=.8)->tuple[OrientedSignature,...]:
    w,h=size
    if w<=0 or h<=0:raise ValueError('image dimensions must be positive')
    if neighbours<2:raise ValueError('neighbours must be at least 2')
    result=[]
    for index,p in enumerate(points):
        px,py=p.x/w,p.y/h;nearby=[]
        for j,q in enumerate(points):
            if j==index:continue
            dx=q.x/w-px;dy=q.y/h-py;nearby.append((hypot(dx,dy),(atan2(dy,dx)%(2*pi))/(2*pi)))
        nearby.sort(key=lambda item:item[0]);chosen=nearby[:neighbours]
        if len(chosen)<2:continue
        distances=tuple(v[0] for v in chosen);angles=sorted(v[1] for v in chosen)
        gaps=tuple(sorted((angles[(i+1)%len(angles)]-angles[i])%1.0 for i in range(len(angles))))
        crossing=(p.crossing_angle_deg/90.0)*angle_weight
        result.append(OrientedSignature(p,distances+gaps+(crossing,)))
    return tuple(result)


def _distance(a:OrientedSignature,b:OrientedSignature)->float:
    if len(a.values)!=len(b.values):return float('inf')
    return sum((x-y)**2 for x,y in zip(a.values,b.values))**.5


def match_oriented_points(thermal_points:tuple[OrientedStructuralPoint,...],rgb_points:tuple[OrientedStructuralPoint,...],*,thermal_size:tuple[int,int]=(640,512),rgb_size:tuple[int,int]=(4000,3000),neighbours:int=5,max_score:float=.2,ambiguity_margin:float=.025,maximum_crossing_angle_delta_deg:float=12,topology_weight:float=.08,maximum_topology_distance:float=.45)->tuple[OrientedMatch,...]:
    """Require compatible crossing angles, PV-grid topology and distinctive geometry."""
    if topology_weight<0:raise ValueError('topology_weight must be non-negative')
    ts=oriented_signatures(thermal_points,thermal_size,neighbours=neighbours);rs=oriented_signatures(rgb_points,rgb_size,neighbours=neighbours)
    if not ts or not rs:return ()
    tt={id(s.point):s for s in grid_topology_signatures(thermal_points,thermal_size)}
    rt={id(s.point):s for s in grid_topology_signatures(rgb_points,rgb_size)}
    matrix=[]
    for t in ts:
        row=[]
        for r in rs:
            if abs(t.point.crossing_angle_deg-r.point.crossing_angle_deg)>maximum_crossing_angle_delta_deg:row.append(float('inf'));continue
            topo=topology_distance(tt[id(t.point)],rt[id(r.point)])
            if topo==float('inf') or topo>maximum_topology_distance:row.append(float('inf'));continue
            row.append(_distance(t,r)+topology_weight*topo)
        matrix.append(row)
    tb=[]
    for row in matrix:
        ranked=sorted(range(len(row)),key=row.__getitem__);best=ranked[0];second=row[ranked[1]] if len(ranked)>1 else float('inf');tb.append((best,row[best],second))
    rb=[]
    for j in range(len(rs)):
        ranked=sorted(range(len(ts)),key=lambda i:matrix[i][j]);best=ranked[0];second=matrix[ranked[1]][j] if len(ranked)>1 else float('inf');rb.append((best,matrix[best][j],second))
    matches=[]
    for i,(j,score,second) in enumerate(tb):
        reverse,_,reverse_second=rb[j]
        if reverse!=i or score==float('inf') or score>max_score:continue
        if second-score<ambiguity_margin or reverse_second-score<ambiguity_margin:continue
        matches.append(OrientedMatch(ts[i].point,rs[j].point,score))
    return tuple(sorted(matches,key=lambda m:m.score))


def split_oriented_matches(matches:tuple[OrientedMatch,...],*,holdout_fraction:float=.3,minimum_holdout:int=4)->tuple[tuple[ControlPoint,...],tuple[ControlPoint,...]]:
    if not 0<holdout_fraction<1:raise ValueError('holdout_fraction must be between 0 and 1')
    ordered=sorted(matches,key=lambda m:(m.thermal.y,m.thermal.x));count=max(minimum_holdout,round(len(ordered)*holdout_fraction));count=min(count,max(0,len(ordered)-4))
    indices={round(i*(len(ordered)-1)/(count-1)) for i in range(count)} if count>1 else ({len(ordered)//2} if count else set())
    def cp(m):return ControlPoint(m.thermal.x,m.thermal.y,m.rgb.x,m.rgb.y)
    return tuple(cp(m) for i,m in enumerate(ordered) if i not in indices),tuple(cp(m) for i,m in enumerate(ordered) if i in indices)
