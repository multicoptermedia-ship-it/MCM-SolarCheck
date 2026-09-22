"""Geometry-aware validation and de-duplication of PV module detections."""
from __future__ import annotations
from dataclasses import dataclass
from math import hypot,isfinite
from mcm_solarcheck.vision.detection import ModuleDetection\nfrom mcm_solarcheck.vision.polygon_geometry import convex_polygon_iou,is_valid_module_polygon

def _area(poly):
    return abs(sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))/2)

def _center(poly):
    return (sum(x for x,_ in poly)/len(poly),sum(y for _,y in poly)/len(poly))

@dataclass(frozen=True)
class ModuleDetectionQuality:
    detection: ModuleDetection
    accepted: bool
    reason: str

def assess_module_detection(detection:ModuleDetection,width:int,height:int,*,minimum_area_fraction:float=.00005,maximum_area_fraction:float=.20)->ModuleDetectionQuality:
    if width<=0 or height<=0: raise ValueError("image dimensions must be positive")
    p=detection.polygon_px
    if not all(isfinite(x) and isfinite(y) for x,y in p): return ModuleDetectionQuality(detection,False,"non_finite")
    if any(x<0 or y<0 or x>=width or y>=height for x,y in p): return ModuleDetectionQuality(detection,False,"outside_image")
    if not is_valid_module_polygon(p): return ModuleDetectionQuality(detection,False,"invalid_polygon")\n    a=_area(p); f=a/(width*height)
    if a<=1e-9: return ModuleDetectionQuality(detection,False,"degenerate_polygon")
    if f<minimum_area_fraction: return ModuleDetectionQuality(detection,False,"too_small")
    if f>maximum_area_fraction: return ModuleDetectionQuality(detection,False,"too_large")
    return ModuleDetectionQuality(detection,True,"accepted")

def _bbox(poly):
    xs=[x for x,_ in poly];ys=[y for _,y in poly];return min(xs),min(ys),max(xs),max(ys)

def _bbox_iou(a,b):
    ax1,ay1,ax2,ay2=_bbox(a);bx1,by1,bx2,by2=_bbox(b)
    inter=max(0,min(ax2,bx2)-max(ax1,bx1))*max(0,min(ay2,by2)-max(ay1,by1))
    aa=max(0,ax2-ax1)*max(0,ay2-ay1);bb=max(0,bx2-bx1)*max(0,by2-by1)
    return inter/(aa+bb-inter) if aa+bb-inter>0 else 0

def filter_module_detections(detections:tuple[ModuleDetection,...],width:int,height:int,*,duplicate_iou:float=.75)->tuple[ModuleDetection,...]:
    """Fail closed on invalid geometry and suppress high-overlap duplicate detections."""
    if not 0<duplicate_iou<=1: raise ValueError("duplicate_iou must be in (0,1]")
    valid = [q.detection for q in (assess_module_detection(d, width, height) for d in detections) if q.accepted and q.detection.class_name == "pv_module"]
    valid.sort(key=lambda d:(-d.confidence,_center(d.polygon_px)))
    kept=[]
    for d in valid:
        if all(convex_polygon_iou(d.polygon_px,k.polygon_px)<duplicate_iou for k in kept): kept.append(d)
    return tuple(kept)
