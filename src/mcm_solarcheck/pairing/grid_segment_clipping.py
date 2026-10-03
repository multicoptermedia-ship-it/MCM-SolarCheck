"""Clip long structural lines into local PV-grid-supported segments."""
from __future__ import annotations
from math import hypot
from .structural_features import StructuralLine,_angle_difference
from .grid_lines import GridLineFamily

def _intersection(a:StructuralLine,b_angle:float,b_offset:float):
    import math
    dx=a.x2-a.x1;dy=a.y2-a.y1
    nx=math.cos(math.radians(b_angle+90));ny=math.sin(math.radians(b_angle+90))
    den=dx*nx+dy*ny
    if abs(den)<1e-9:return None
    t=(b_offset-a.x1*nx-a.y1*ny)/den
    if -1e-6<=t<=1+1e-6:return (t,a.x1+t*dx,a.y1+t*dy)
    return None

def clip_lines_at_crossing_grid(lines:tuple[StructuralLine,...],parallel:GridLineFamily,crossing:GridLineFamily,*,angle_tolerance_deg:float=12.0)->tuple[StructuralLine,...]:
    """Split long parallel segments at observed crossings of the other grid axis."""
    if not 0<angle_tolerance_deg<45:raise ValueError('angle_tolerance_deg must be between 0 and 45')
    out=[]
    for line in lines:
        if _angle_difference(line.angle_deg,parallel.angle_deg)>angle_tolerance_deg:continue
        cuts=[(0.0,line.x1,line.y1),(1.0,line.x2,line.y2)]
        for grid in crossing.lines:
            hit=_intersection(line,grid.angle_deg,grid.offset_px)
            if hit is not None:cuts.append(hit)
        cuts=sorted(cuts,key=lambda p:p[0])
        unique=[]
        for item in cuts:
            if not unique or abs(item[0]-unique[-1][0])>1e-6:unique.append(item)
        for a,b in zip(unique,unique[1:]):
            length=hypot(b[1]-a[1],b[2]-a[2])
            if length>1e-6:out.append(StructuralLine(a[1],a[2],b[1],b[2],length,line.angle_deg))
    return tuple(out)
