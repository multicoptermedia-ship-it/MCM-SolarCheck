"""Polygon geometry helpers for PV-module quality gates."""
from __future__ import annotations
import cv2,numpy as np

def convex_polygon_iou(a,b)->float:
    pa=np.asarray(a,dtype=np.float32);pb=np.asarray(b,dtype=np.float32)
    if len(pa)<3 or len(pb)<3:return 0.0
    aa=abs(cv2.contourArea(pa));ab=abs(cv2.contourArea(pb))
    if aa<=0 or ab<=0:return 0.0
    inter,_=cv2.intersectConvexConvex(pa,pb)
    union=aa+ab-float(inter)
    return float(inter)/union if union>0 else 0.0

def is_valid_module_polygon(poly)->bool:
    p=np.asarray(poly,dtype=np.float32)
    return len(p)>=4 and cv2.isContourConvex(p) and abs(cv2.contourArea(p))>0
