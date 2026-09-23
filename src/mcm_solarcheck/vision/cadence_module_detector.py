"""Cadence-aware confirmed detector: grid geometry may only survive independent image evidence."""
from __future__ import annotations
from pathlib import Path
import cv2
from mcm_solarcheck.pairing.structural_features import detect_structural_lines
from mcm_solarcheck.pairing.grid_lines import extract_grid_line_families
from mcm_solarcheck.vision.opencv_module_detector import OpenCVModuleDetector
from mcm_solarcheck.vision.cadence_gate import assess_ambiguous_module_cadence
from mcm_solarcheck.vision.cadence_phase_selection import select_cadence_phase
from mcm_solarcheck.vision.grid_module_detector import grid_module_detections
from mcm_solarcheck.vision.grid_cadence import cadence_line_subsets
from mcm_solarcheck.vision.grid_cell_support import filter_cells_by_finite_support
from mcm_solarcheck.vision.module_fusion import fuse_module_detections
from mcm_solarcheck.vision.detection import ModuleDetection

class CadenceConfirmedModuleDetector:
    name="cadence_confirmed_pv_module_v1"
    def __init__(self,*,max_dimension:int=900,minimum_iou:float=.20):self.max_dimension=max_dimension;self.minimum_iou=minimum_iou;self.image_detector=OpenCVModuleDetector()
    def detect(self,source_file:Path)->tuple[ModuleDetection,...]:
        image=cv2.imread(str(source_file),cv2.IMREAD_COLOR)
        if image is None:return ()
        h,w=image.shape[:2];scale=min(1.0,self.max_dimension/max(h,w));small=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA) if scale<1 else image
        lines=detect_structural_lines(small,max_dimension=self.max_dimension,min_length_fraction=.08);families=extract_grid_line_families(lines)
        support_full=self.image_detector.detect(source_file)
        support=tuple(ModuleDetection(tuple((x*scale,y*scale) for x,y in d.polygon_px),d.confidence,d.class_name) for d in support_full)
        gate=assess_ambiguous_module_cadence(families,support,lines,small.shape[1],small.shape[0],minimum_iou=self.minimum_iou)
        if not gate.accepted:return ()
        multiples=tuple(int(a.dominant_multiple) for a in gate.axes)
        if gate.phases is None:
            phase=select_cadence_phase(families,multiples,support,small.shape[1],small.shape[0],minimum_iou=self.minimum_iou)
            if not phase.accepted:return ()
            selected_families=phase.families
        else:
            subsets=tuple(cadence_line_subsets(f,m) for f,m in zip(families,multiples))
            if len(gate.phases)!=2 or len(subsets)!=2:return ()
            if any(p<0 or p>=len(s) for s,p in zip(subsets,gate.phases)):return ()
            selected_families=tuple(s[p] for s,p in zip(subsets,gate.phases))
        expected=tuple(float(a.median_gap_px)*int(a.dominant_multiple) for a in gate.axes)
        cells=grid_module_detections(selected_families,small.shape[1],small.shape[0],margin_px=2,expected_gaps_px=expected)
        cells=filter_cells_by_finite_support(cells,selected_families,lines)
        if scale<1:cells=tuple(ModuleDetection(tuple((x/scale,y/scale) for x,y in d.polygon_px),d.confidence,d.class_name) for d in cells)
        return fuse_module_detections(cells,support_full,minimum_iou=self.minimum_iou)
