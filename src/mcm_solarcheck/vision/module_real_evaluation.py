"""Build development evaluation from independent detector outputs."""
from __future__ import annotations
from mcm_solarcheck.vision.module_diagnostics import diagnose_module_evidence
from mcm_solarcheck.vision.module_evaluation import ModuleFrameEvaluation,ModuleDevelopmentEvaluation

def evaluate_detector_pair(frames,grid_detector,image_detector,*,minimum_iou:float=.20)->ModuleDevelopmentEvaluation:
    rows=[]
    for frame in frames:
        grid=tuple(grid_detector.detect(frame.source_file));image=tuple(image_detector.detect(frame.source_file))
        q=diagnose_module_evidence(grid,image,minimum_iou=minimum_iou)
        rows.append(ModuleFrameEvaluation(frame.frame_id,q.grid_candidates,q.image_candidates,q.confirmed,q.status))
    return ModuleDevelopmentEvaluation(tuple(rows))
