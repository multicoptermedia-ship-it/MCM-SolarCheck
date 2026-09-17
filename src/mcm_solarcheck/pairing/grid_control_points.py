"""Build thermal/RGB control points from matched global PV grid lines."""
from __future__ import annotations
from math import cos,radians,sin
from .grid_lines import GridLine
from .grid_line_matching import GridLineFamilyMatch
from .registration import ControlPoint


def _selected(match:GridLineFamilyMatch,sensor:str)->tuple[GridLine,...]:
    if sensor=='thermal':return match.thermal.lines[match.start_thermal:match.start_thermal+match.count]
    lines=tuple(reversed(match.rgb.lines)) if match.reversed_order else match.rgb.lines
    return lines[match.start_rgb:match.start_rgb+match.count]


def _intersection(a:GridLine,b:GridLine)->tuple[float,float]|None:
    # GridLine is represented in normal form n.x=offset, where n is angle+90.
    na=radians(a.angle_deg+90);nb=radians(b.angle_deg+90)
    a1,b1=cos(na),sin(na);a2,b2=cos(nb),sin(nb);det=a1*b2-b1*a2
    if abs(det)<1e-8:return None
    return ((a.offset_px*b2-b1*b.offset_px)/det,(a1*b.offset_px-a.offset_px*a2)/det)


def grid_control_points(matches:tuple[GridLineFamilyMatch,...],*,minimum_crossing_angle_deg:float=45)->tuple[ControlPoint,...]:
    """Create indexed line-intersection correspondences from two family matches."""
    if len(matches)!=2:return ()
    first,second=matches
    d=abs(first.thermal.angle_deg-second.thermal.angle_deg)%180;d=min(d,180-d)
    r=abs(first.rgb.angle_deg-second.rgb.angle_deg)%180;r=min(r,180-r)
    if d<minimum_crossing_angle_deg or r<minimum_crossing_angle_deg:return ()
    ta=_selected(first,'thermal');tb=_selected(second,'thermal');ra=_selected(first,'rgb');rb=_selected(second,'rgb')
    points=[]
    for i,(tl,rl) in enumerate(zip(ta,ra)):
        for j,(tm,rm) in enumerate(zip(tb,rb)):
            tp=_intersection(tl,tm);rp=_intersection(rl,rm)
            if tp is None or rp is None:continue
            points.append(ControlPoint(tp[0],tp[1],rp[0],rp[1]))
    return tuple(points)


def split_grid_control_points(points:tuple[ControlPoint,...],*,minimum_fit:int=6,minimum_holdout:int=4)->tuple[tuple[ControlPoint,...],tuple[ControlPoint,...]]:
    """Deterministically reserve spatially distributed intersections for validation."""
    if len(points)<minimum_fit+minimum_holdout:return (),()
    ordered=sorted(points,key=lambda p:(p.thermal_y,p.thermal_x))
    count=max(minimum_holdout,round(len(ordered)*.3));count=min(count,len(ordered)-minimum_fit)
    indices={round(i*(len(ordered)-1)/(count-1)) for i in range(count)} if count>1 else {len(ordered)//2}
    fit=tuple(p for i,p in enumerate(ordered) if i not in indices);holdout=tuple(p for i,p in enumerate(ordered) if i in indices)
    return fit,holdout
