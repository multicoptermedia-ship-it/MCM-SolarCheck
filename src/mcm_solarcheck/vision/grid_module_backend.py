"""Grid-backed PV module detector using the established structural feature stack."""
from __future__ import annotations
from pathlib import Path
import cv2
from mcm_solarcheck.pairing.structural_features import detect_structural_lines
from mcm_solarcheck.pairing.grid_lines import extract_grid_line_families
from mcm_solarcheck.vision.grid_module_detector import grid_module_detections

class GridModuleDetector:
    name="structural_grid_v1"
    def __init__(self,*,max_dimension:int=900):
        if max_dimension<=0: raise ValueError("max_dimension must be positive")
        self.max_dimension=max_dimension

    def detect(self,source_file:Path):
        image=cv2.imread(str(source_file),cv2.IMREAD_COLOR)
        if image is None:return ()
        h,w=image.shape[:2]
        scale=min(1.0,self.max_dimension/max(h,w))
        small=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA) if scale<1 else image
        lines=detect_structural_lines(small,max_dimension=self.max_dimension,min_length_fraction=.08)
        families=extract_grid_line_families(lines)
        detections=grid_module_detections(families,small.shape[1],small.shape[0],margin_px=2)
        if scale==1:return detections
        from mcm_solarcheck.vision.detection import ModuleDetection
        return tuple(ModuleDetection(tuple((x/scale,y/scale) for x,y in d.polygon_px),d.confidence,d.class_name) for d in detections)
