"""Visible PV grid boundary evidence.

Unlike extrapolated grid envelopes, these candidates are accepted only when an
extreme grid line has observed segment support close to a real image endpoint.
The module extracts evidence; it does not yet establish cross-sensor identity.
"""
from dataclasses import dataclass
from math import hypot
from .structural_features import StructuralLine
from .grid_lines import GridLineFamily

@dataclass(frozen=True)
class VisibleBoundary:
    family_index:int
    side:str
    endpoint:tuple[float,float]
    support_length_px:float

def _distance_point_to_line_endpoint(x:float,y:float,line:StructuralLine)->float:
    return min(hypot(x-line.x1,y-line.y1),hypot(x-line.x2,y-line.y2))

def visible_grid_boundaries(lines:tuple[StructuralLine,...],families:tuple[GridLineFamily,...],*,endpoint_tolerance_px:float=18.0,angle_tolerance_deg:float=12.0)->tuple[VisibleBoundary,...]:
    """Return extreme-family boundaries backed by an observed segment endpoint."""
    from .structural_features import _angle_difference
    if endpoint_tolerance_px<=0:raise ValueError('endpoint_tolerance_px must be positive')
    if not 0<angle_tolerance_deg<45:raise ValueError('angle_tolerance_deg must be between 0 and 45')
    out=[]
    for fi,family in enumerate(families):
        if len(family.lines)<2:continue
        for side,grid in (('first',family.lines[0]),('last',family.lines[-1])):
            candidates=[]
            for line in lines:
                if _angle_difference(line.angle_deg,family.angle_deg)>angle_tolerance_deg:continue
                # Compare segment midpoint's signed normal offset with the clustered line.
                import math
                mx=(line.x1+line.x2)/2;my=(line.y1+line.y2)/2
                n=math.radians(family.angle_deg+90)
                if abs(mx*math.cos(n)+my*math.sin(n)-grid.offset_px)>endpoint_tolerance_px:continue
                candidates.append(line)
            if not candidates:continue
            support=max(candidates,key=lambda line:line.length)
            # Endpoint is evidence that the detected extreme is visibly supported,
            # not proof of which physical module row/column it represents.
            ep=(support.x1,support.y1) if (support.x1,support.y1)<(support.x2,support.y2) else (support.x2,support.y2)
            out.append(VisibleBoundary(fi,side,ep,support.length))
    return tuple(out)
