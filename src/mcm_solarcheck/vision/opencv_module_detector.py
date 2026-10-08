"""Conservative OpenCV fallback detector for visually distinct PV modules."""
from __future__ import annotations
from pathlib import Path
import cv2
import numpy as np
from mcm_solarcheck.vision.detection import ModuleDetection

class OpenCVModuleDetector:
    """Detect isolated blue/dark module surfaces without model weights.

    This fallback intentionally prefers false negatives over roof false positives.
    A learned detector can implement the same execution protocol.
    """
    name="opencv_pv_module_v1"
    def __init__(self,*,max_dimension:int=1000,minimum_saturation:int=25,maximum_value:int=205):
        if max_dimension<=0: raise ValueError("max_dimension must be positive")
        self.max_dimension=max_dimension;self.minimum_saturation=minimum_saturation;self.maximum_value=maximum_value

    def detect(self,source_file:Path)->tuple[ModuleDetection,...]:
        image=cv2.imread(str(source_file),cv2.IMREAD_COLOR)
        if image is None: return ()
        h,w=image.shape[:2]; scale=min(1.0,self.max_dimension/max(h,w))
        small=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA) if scale<1 else image
        hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
        mask=((hsv[:,:,1]>=self.minimum_saturation)&(hsv[:,:,2]<=self.maximum_value)).astype(np.uint8)*255
        mask=cv2.erode(mask,np.ones((3,3),np.uint8),iterations=1)
        n,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
        image_area=small.shape[0]*small.shape[1]; out=[]
        for i in range(1,n):
            area=float(stats[i,cv2.CC_STAT_AREA]); fraction=area/image_area
            if not .0015<=fraction<=.02: continue
            ys,xs=np.where(labels==i); pts=np.column_stack((xs,ys)).astype(np.float32)
            rect=cv2.minAreaRect(pts); rw,rh=rect[1]
            if min(rw,rh)<=0: continue
            aspect=max(rw,rh)/min(rw,rh); fill=area/(rw*rh)
            if not 1.25<=aspect<=2.8 or fill<.50: continue
            box=cv2.boxPoints(rect)/scale
            poly=tuple((float(x),float(y)) for x,y in box)
            confidence=min(.90,.50+.25*min(fill,1)+.15*min(1,area/(.006*image_area)))
            out.append(ModuleDetection(poly,confidence))
        return tuple(out)
