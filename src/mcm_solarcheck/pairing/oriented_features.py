"""Oriented structural intersections for cross-spectral PV registration.

Intersections retain their generating line orientations and must be supported by
the detected finite segments. A small configurable extension tolerates broken PV
frame edges without accepting arbitrary infinite-line crossings.
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


def _segment_support(line:StructuralLine,x:float,y:float,extension_fraction:float)->bool:
    """Return whether a point lies on a segment, allowing bounded end extension."""
    dx=line.x2-line.x1;dy=line.y2-line.y1;length2=dx*dx+dy*dy
    if length2<=1e-12:return False
    t=((x-line.x1)*dx+(y-line.y1)*dy)/length2
    extension=extension_fraction
    if t < -extension or t > 1.0+extension:return False
    # Intersection was computed from the infinite line; keep a small numerical guard.
    nearest_x=line.x1+t*dx;nearest_y=line.y1+t*dy
    return hypot(x-nearest_x,y-nearest_y)<=max(1.0,line.length*.01)


def oriented_intersections(lines:tuple[StructuralLine,...],width:int,height:int,*,minimum_angle_deg:float=25,margin_fraction:float=.03,max_points:int=300,dedup_distance_px:float=5,segment_extension_fraction:float=.18)->tuple[OrientedStructuralPoint,...]:
    """Return unique, segment-supported line intersections with orientations."""
    if width<=0 or height<=0:raise ValueError('image dimensions must be positive')
    if dedup_distance_px<0:raise ValueError('dedup_distance_px must be non-negative')
    if segment_extension_fraction<0:raise ValueError('segment_extension_fraction must be non-negative')
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
            if not _segment_support(a,px,py,segment_extension_fraction):continue
            if not _segment_support(b,px,py,segment_extension_fraction):continue
            point=OrientedStructuralPoint(float(px),float(py),a.angle_deg,b.angle_deg)
            duplicate=next((j for j,p in enumerate(points) if hypot(point.x-p.x,point.y-p.y)<=dedup_distance_px),None)
            if duplicate is None:points.append(point)
            elif point.crossing_angle_deg>points[duplicate].crossing_angle_deg:points[duplicate]=point
            if len(points)>=max_points:break
        if len(points)>=max_points:break
    return tuple(points)
