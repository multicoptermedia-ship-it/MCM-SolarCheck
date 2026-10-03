"""Deterministic CSV-like rows for inspecting module detection development runs."""
from __future__ import annotations
from mcm_solarcheck.vision.module_evaluation import ModuleDevelopmentEvaluation

def evaluation_rows(e:ModuleDevelopmentEvaluation)->tuple[tuple[str,int,int,int,str],...]:
    return tuple((f.frame_id,f.grid_candidates,f.image_candidates,f.confirmed,f.status) for f in e.frames)

def evaluation_summary(e:ModuleDevelopmentEvaluation)->dict[str,int]:
    return {"processed":e.processed,"confirmed_total":e.confirmed_total,"failure_frames":len(e.failure_frames)}
