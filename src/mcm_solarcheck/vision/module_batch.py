"""Batch execution for PV-module detection with auditable per-frame status."""
from __future__ import annotations
from dataclasses import dataclass
from mcm_solarcheck.domain.models import ImageFrame
from mcm_solarcheck.vision.module_detection_pipeline import ModuleDetectionRun,detect_modules_in_frame

@dataclass(frozen=True)
class ModuleBatchResult:
    runs:tuple[ModuleDetectionRun,...]
    @property
    def detected_frames(self):return sum(r.status=="detected" for r in self.runs)
    @property
    def module_count(self):return sum(len(r.modules) for r in self.runs)

def detect_modules_batch(frames:tuple[ImageFrame,...],detector)->ModuleBatchResult:
    runs=tuple(detect_modules_in_frame(frame,detector) for frame in frames)
    return ModuleBatchResult(runs)
