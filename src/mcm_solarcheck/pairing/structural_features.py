"""Cross-spectral structural features for M3T RGB/thermal registration.

Appearance descriptors are intentionally avoided. The detector extracts long
edges and their intersections, which are more likely to correspond to PV module
frames and roof geometry in both modalities.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import atan2,degrees,hypot
import cv2
import numpy as np

@dataclass(frozen=True)
class StructuralLine:
    x1:float;y1:float;x2:float;y2:float;length:float;angle_deg:float

@dataclass(frozen=True)
class StructuralPoint:
    x:float;y:float


def detect_structural_lines(image:np.ndarray,*,max_dimension:int=900,min_length_fraction:float=.12,max_lines:int=120,angle_bin_deg:int=15)->tuple[StructuralLine,...]:
    if image is None or image.size==0:raise ValueError('image must not be empty')
    if angle_bin_deg<=0 or 180%angle_bin_deg:raise ValueError('angle_bin_deg must divide 180')
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) if image.ndim==3 else image.copy()
    h,w=gray.shape[:2];scale=min(1.0,max_dimension/max(h,w))
    work=cv2.resize(gray,(round(w*scale),round(h*scale)),interpolation=cv2.INTER_AREA) if scale<1 else gray
    work=cv2.GaussianBlur(work,(5,5),0);edges=cv2.Canny(work,50,150)
    minimum=max(20,int(min(work.shape[:2])*min_length_fraction))
    raw=cv2.HoughLinesP(edges,1,np.pi/180,threshold=max(35,minimum//2),minLineLength=minimum,maxLineGap=max(8,minimum//8))
    if raw is None:return ()
    segments=np.asarray(raw).reshape(-1,4)
    inv=1.0/scale;bins={index:[] for index in range(180//angle_bin_deg)}
    for x1,y1,x2,y2 in segments:
        x1=float(x1)*inv;y1=float(y1)*inv;x2=float(x2)*inv;y2=float(y2)*inv;length=hypot(x2-x1,y2-y1);angle=(degrees(atan2(y2-y1,x2-x1))+180)%180
        line=StructuralLine(x1,y1,x2,y2,length,angle);bins[min(int(angle//angle_bin_deg),len(bins)-1)].append(line)
    for bucket in bins.values():bucket.sort(key=lambda line:line.length,reverse=True)
    selected=[];depth=0
    while len(selected)<max_lines:
        added=False
        for bucket in bins.values():
            if depth<len(bucket):selected.append(bucket[depth]);added=True
            if len(selected)>=max_lines:break
        if not added:break
        depth+=1
    return tuple(selected)


def _angle_difference(a:float,b:float)->float:
    d=abs(a-b)%180;return min(d,180-d)


def structural_intersections(lines:tuple[StructuralLine,...],width:int,height:int,*,minimum_angle_deg:float=25,margin_fraction:float=.03,max_points:int=300)->tuple[StructuralPoint,...]:
    """Return intersections of sufficiently non-parallel long structural lines."""
    margin=max(width,height)*margin_fraction;points=[]
    for i,a in enumerate(lines):
        for b in lines[i+1:]:
            if _angle_difference(a.angle_deg,b.angle_deg)<minimum_angle_deg:continue
            x1,y1,x2,y2=a.x1,a.y1,a.x2,a.y2;x3,y3,x4,y4=b.x1,b.y1,b.x2,b.y2
            den=(x1-x2)*(y3-y4)-(y1-y2)*(x3-x4)
            if abs(den)<1e-9:continue
            px=((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/den
            py=((x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4))/den
            if -margin<=px<=width+margin and -margin<=py<=height+margin:points.append(StructuralPoint(float(px),float(py)))
    unique=[]
    for point in points:
        if all(hypot(point.x-other.x,point.y-other.y)>5 for other in unique):unique.append(point)
        if len(unique)>=max_points:break
    return tuple(unique)
