"""Require finite observed structural segments to support proposed PV grid cells."""
from __future__ import annotations
from math import hypot
from mcm_solarcheck.pairing.structural_features import StructuralLine,_angle_difference
from mcm_solarcheck.pairing.grid_lines import GridLineFamily
from mcm_solarcheck.vision.detection import ModuleDetection

def _point_segment_distance(p,line):
 x,y=p;dx=line.x2-line.x1;dy=line.y2-line.y1
 if dx*dx+dy*dy<=1e-9:return hypot(x-line.x1,y-line.y1)
 t=max(0.0,min(1.0,((x-line.x1)*dx+(y-line.y1)*dy)/(dx*dx+dy*dy)))
 return hypot(x-(line.x1+t*dx),y-(line.y1+t*dy))

def _side_supported(a,b,lines,angle,tolerance):
 # Fragmented support is valid only when both endpoint-supporting fragments lie
 # close to the same expected finite side, not merely somewhere near each corner.
 dx=b[0]-a[0];dy=b[1]-a[1];length=hypot(dx,dy)
 if length<=1e-9:return False
 def line_distance(p):
  return abs(dy*(p[0]-a[0])-dx*(p[1]-a[1]))/length
 candidates=[line for line in lines if _angle_difference(line.angle_deg,angle)<=12 and
             line_distance((line.x1,line.y1))<=tolerance and line_distance((line.x2,line.y2))<=tolerance]
 return (any(_point_segment_distance(a,line)<=tolerance for line in candidates) and
         any(_point_segment_distance(b,line)<=tolerance for line in candidates))

def finite_support_sides(cell:ModuleDetection,families:tuple[GridLineFamily,...],lines:tuple[StructuralLine,...],*,tolerance_px:float=12)->tuple[bool,bool,bool,bool]:
 """Return observed finite support for the four ordered cell sides."""
 if tolerance_px<=0:raise ValueError("tolerance_px must be positive")
 if len(families)!=2 or len(cell.polygon_px)!=4:return (False,False,False,False)
 p=cell.polygon_px;a,b=families
 return (_side_supported(p[0],p[1],lines,b.angle_deg,tolerance_px),
         _side_supported(p[2],p[3],lines,b.angle_deg,tolerance_px),
         _side_supported(p[1],p[2],lines,a.angle_deg,tolerance_px),
         _side_supported(p[3],p[0],lines,a.angle_deg,tolerance_px))

def filter_cells_by_finite_support(cells:tuple[ModuleDetection,...],families:tuple[GridLineFamily,...],lines:tuple[StructuralLine,...],*,tolerance_px:float=12)->tuple[ModuleDetection,...]:
 """Keep cells whose four sides are each backed by an observed finite segment."""
 if tolerance_px<=0:raise ValueError("tolerance_px must be positive")
 if len(families)!=2:return ()
 out=[];a,b=families
 for cell in cells:
  p=cell.polygon_px
  if len(p)!=4:continue
  if all(finite_support_sides(cell,families,lines,tolerance_px=tolerance_px)):out.append(cell)
 return tuple(out)
