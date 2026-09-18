"""PV grid envelope anchors for cross-sensor registration.

The outer intersections of two ordered grid-line families provide semantic
array/block boundary candidates.  This module only extracts geometry; it does
not claim that an observed outer line is a physical array boundary.
"""
from dataclasses import dataclass
from .grid_lines import GridLine,GridLineFamily

@dataclass(frozen=True)
class GridEnvelope:
    corners:tuple[tuple[float,float],...]
    width_lines:int
    height_lines:int

def _intersection(a:GridLine,b:GridLine)->tuple[float,float]|None:
    import math
    # Lines use signed normal offset: x*cos(a+90)+y*sin(a+90)=offset.
    n1=math.radians(a.angle_deg+90.0);n2=math.radians(b.angle_deg+90.0)
    a1,b1=math.cos(n1),math.sin(n1);a2,b2=math.cos(n2),math.sin(n2)
    det=a1*b2-a2*b1
    if abs(det)<1e-9:return None
    return ((a.offset_px*b2-b.offset_px*b1)/det,(a1*b.offset_px-a2*a.offset_px)/det)

def grid_envelope(first:GridLineFamily,second:GridLineFamily)->GridEnvelope|None:
    """Return four extreme grid intersections in stable family order."""
    if len(first.lines)<2 or len(second.lines)<2:return None
    pairs=((first.lines[0],second.lines[0]),(first.lines[-1],second.lines[0]),
           (first.lines[-1],second.lines[-1]),(first.lines[0],second.lines[-1]))
    corners=tuple(_intersection(a,b) for a,b in pairs)
    if any(p is None for p in corners):return None
    return GridEnvelope(corners=corners,width_lines=len(first.lines),height_lines=len(second.lines))
