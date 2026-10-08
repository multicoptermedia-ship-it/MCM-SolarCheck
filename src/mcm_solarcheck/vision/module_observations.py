"""Stable, rotation-invariant conversion of confirmed PV modules to identity observations."""
from __future__ import annotations
from math import hypot
from mcm_solarcheck.vision.module_identity import ModuleObservation

def _polygon_area(p):
    return abs(sum(x1*y2-x2*y1 for (x1,y1),(x2,y2) in zip(p,p[1:]+p[:1])))/2.0

def module_observations(modules)->tuple[ModuleObservation,...]:
    out=[]
    for m in modules:
        p=tuple(m.polygon_px)
        if len(p)<3:raise ValueError("module polygon needs at least three points")
        area=_polygon_area(p)
        if area<=0:raise ValueError("module polygon must have positive area")
        # Use area plus the longest polygon edge. Unlike an axis-aligned bounding box,
        # these dimensions are invariant under image-plane rotation.
        edges=[hypot(x2-x1,y2-y1) for (x1,y1),(x2,y2) in zip(p,p[1:]+p[:1])]
        long=max(edges)
        short=area/long
        cx=sum((x1+x2)*(x1*y2-x2*y1) for (x1,y1),(x2,y2) in zip(p,p[1:]+p[:1]))/(6*sum(x1*y2-x2*y1 for (x1,y1),(x2,y2) in zip(p,p[1:]+p[:1]))) * 2
        cy=sum((y1+y2)*(x1*y2-x2*y1) for (x1,y1),(x2,y2) in zip(p,p[1:]+p[:1]))/(6*sum(x1*y2-x2*y1 for (x1,y1),(x2,y2) in zip(p,p[1:]+p[:1]))) * 2
        out.append(ModuleObservation(m.frame_id,m.module_id,(cx,cy),short,long))
    return tuple(out)
