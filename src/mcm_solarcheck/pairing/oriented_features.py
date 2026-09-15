"""Oriented structural intersections for cross-spectral PV registration.

Unlike plain points, an oriented intersection keeps the two line directions that
created it. The acute crossing angle is invariant to image rotation and gives the
matcher an additional modality-independent geometric constraint.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import hypot
from .structural_features import StructuralLine,_angle_difference

@dataclass(frozen=True)
class OrientedStructuralPoint:
    x:float
    y:float
    angle_a_deg:float
    angle_b_deg:float

    @property
    def crossing_angle_deg(self)->float:
        return _angle_difference(self.angle_a_deg,self.angle_b_deg)


def oriented_intersections(lines:tuple[StructuralLine,...],width:int,height:int,*,minimum_angle_deg:float=25,margin_fraction:float=.03,max_points:int=300,dedup_distance_px:float=5)->tuple[OrientedStructuralPoint,...]:
    """Return unique line intersections while preserving their line orientations."""
    if width<=0 or height<=0:raise ValueError('image dimensions must be positive')
    if dedup_distance_px<0:raise ValueError('dedup_distance_px must be non-negative')
    margin=max(width,height)*margin_fraction;points=[]
    for i,a in enumerate(lines):
        for b in lines[i+1:]:
            if _angle_difference(a.angle_deg,b.angle_deg)<minimum_angle_deg:continue
            x1,y1,x2,y2=a.x1,a.y1,a.x2,a.y2;x3,y3,x4,y4=b.x1,b.y1,b.x2,b.y2
            den=(x1-x2)*(y3-y4)-(y1-y2)*(x3-x4)
            if abs(den)<1e-9:continue
            px=((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/den
            py=((x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4))/den
            if not (-margin<=px<=width+margin and -margin<=py<=height+margin):continue
            point=OrientedStructuralPoint(float(px),float(py),a.angle_deg,b.angle_deg)
            # Prefer a stronger, more orthogonal crossing when several line pairs meet
            # at effectively the same image point.
            duplicate=next((j for j,p in enumerate(points) if hypot(point.x-p.x,point.y-p.y)<=dedup_distance_px),None)
            if duplicate is None:points.append(point)
            elif point.crossing_angle_deg>points[duplicate].crossing_angle_deg:points[duplicate]=point
            if len(points)>=max_points:break
        if len(points)>=max_points:break
    return tuple(points)
