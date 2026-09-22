"""Acceptance gates for PV-module detection development runs."""
from __future__ import annotations
from dataclasses import dataclass
from mcm_solarcheck.vision.module_evaluation import ModuleDevelopmentEvaluation

@dataclass(frozen=True)
class ModuleAcceptance:
    accepted:bool
    reason:str

def assess_development_run(evaluation:ModuleDevelopmentEvaluation,*,minimum_processed:int=1,require_all_confirmed:bool=False)->ModuleAcceptance:
    if evaluation.processed<minimum_processed:return ModuleAcceptance(False,"insufficient_frames")
    if evaluation.confirmed_total<=0:return ModuleAcceptance(False,"no_confirmed_modules")
    if require_all_confirmed and evaluation.failure_frames:return ModuleAcceptance(False,"frames_without_confirmation")
    return ModuleAcceptance(True,"accepted")
