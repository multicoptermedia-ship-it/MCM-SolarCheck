"""Diagnostics for conservative PV-module detection decisions."""
from __future__ import annotations
from dataclasses import dataclass
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.module_fusion import fuse_module_detections

@dataclass(frozen=True)
class ModuleDetectionDiagnostics:
    grid_candidates:int
    image_candidates:int
    confirmed:int
    rejected_unconfirmed:int
    status:str

def diagnose_module_evidence(grid:tuple[ModuleDetection,...],image:tuple[ModuleDetection,...],*,minimum_iou:float=.20)->ModuleDetectionDiagnostics:
    confirmed=fuse_module_detections(grid,image,minimum_iou=minimum_iou)
    if not grid:status="no_grid_geometry"
    elif not image:status="no_image_support"
    elif not confirmed:status="evidence_disagrees"
    else:status="confirmed"
    return ModuleDetectionDiagnostics(len(grid),len(image),len(confirmed),len(grid)-len(confirmed),status)
