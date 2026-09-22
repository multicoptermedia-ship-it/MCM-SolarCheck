"""Derive module-cell polygons from two validated PV grid-line families."""
from __future__ import annotations
from dataclasses import dataclass
from math import cos,sin,radians,isfinite
from mcm_solarcheck.pairing.grid_lines import GridLineFamily
from mcm_solarcheck.vision.detection import ModuleDetection

def _intersection(a,b):
    aa=radians(a.angle_deg+90);bb=radians(b.angle_deg+90)
    n1=(cos(aa),sin(aa));n2=(cos(bb),sin(bb));det=n1[0]*n2[1]-n1[1]*n2[0]
    if abs(det)<1e-6:return None
    return ((a.offset_px*n2[1]-n1[1]*b.offset_px)/det,(n1[0]*b.offset_px-a.offset_px*n2[0])/det)

def grid_module_detections(families:tuple[GridLineFamily,...],width:int,height:int,*,margin_px:float=8)->tuple[ModuleDetection,...]:
    """Return only complete adjacent grid cells whose corners lie in the image."""
    if len(families)!=2 or width<=0 or height<=0:return ()
    a,b=families
    if len(a.lines)<2 or len(b.lines)<2:return ()
    la=sorted(a.lines,key=lambda x:x.offset_px);lb=sorted(b.lines,key=lambda x:x.offset_px);out=[]
    for i in range(len(la)-1):
      for j in range(len(lb)-1):
        pts=(_intersection(la[i],lb[j]),_intersection(la[i+1],lb[j]),_intersection(la[i+1],lb[j+1]),_intersection(la[i],lb[j+1]))
        if any(p is None for p in pts):continue
        poly=tuple(pts)
        if not all(isfinite(x) and isfinite(y) and margin_px<=x<width-margin_px and margin_px<=y<height-margin_px for x,y in poly):continue
        out.append(ModuleDetection(poly,.80))
    return tuple(out)
