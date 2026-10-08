"""Composite detector: structural grid geometry confirmed by image evidence."""
from __future__ import annotations
from pathlib import Path
from mcm_solarcheck.vision.grid_module_backend import GridModuleDetector
from mcm_solarcheck.vision.opencv_module_detector import OpenCVModuleDetector
from mcm_solarcheck.vision.module_fusion import fuse_module_detections

class ConfirmedModuleDetector:
    name="grid_plus_image_v1"
    def __init__(self,grid=None,image=None,*,minimum_iou:float=.20):
        self.grid=grid or GridModuleDetector()
        self.image=image or OpenCVModuleDetector()
        self.minimum_iou=minimum_iou
    def detect(self,source_file:Path):
        geometry=tuple(self.grid.detect(source_file))
        if not geometry:return ()
        support=tuple(self.image.detect(source_file))
        return fuse_module_detections(geometry,support,minimum_iou=self.minimum_iou)
