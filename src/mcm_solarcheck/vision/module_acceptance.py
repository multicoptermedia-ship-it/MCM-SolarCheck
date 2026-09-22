"""Acceptance gates for unlabeled PV-module development runs.

These checks establish execution/diagnostic quality, not detector accuracy. Precision and
recall require independently labelled ground truth and are deliberately not inferred here.
"""
from __future__ import annotations
from dataclasses import dataclass
from mcm_solarcheck.vision.module_evaluation import ModuleDevelopmentEvaluation

@dataclass(frozen=True)
class ModuleAcceptance:
    accepted:bool
    reason:str

def assess_development_run(evaluation:ModuleDevelopmentEvaluation,*,minimum_processed:int=1,require_all_confirmed:bool=False)->ModuleAcceptance:
    if minimum_processed<1:return ModuleAcceptance(False,"invalid_minimum_processed")
    if evaluation.processed<minimum_processed:return ModuleAcceptance(False,"insufficient_frames")
    ids=[f.frame_id for f in evaluation.frames]
    if any(not i.strip() for i in ids) or len(set(ids))!=len(ids):return ModuleAcceptance(False,"invalid_frame_identity")
    if any(min(f.grid_candidates,f.image_candidates,f.confirmed)<0 for f in evaluation.frames):return ModuleAcceptance(False,"invalid_counts")
    if any(f.confirmed>f.grid_candidates or f.confirmed>f.image_candidates for f in evaluation.frames):return ModuleAcceptance(False,"inconsistent_counts")
    if evaluation.confirmed_total<=0:return ModuleAcceptance(False,"no_confirmed_modules")
    if require_all_confirmed and evaluation.failure_frames:return ModuleAcceptance(False,"frames_without_confirmation")
    return ModuleAcceptance(True,"accepted")
