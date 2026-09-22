"""Evaluation records for real RGB development data without claiming ground-truth accuracy."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ModuleFrameEvaluation:
    frame_id:str
    grid_candidates:int
    image_candidates:int
    confirmed:int
    status:str

@dataclass(frozen=True)
class ModuleDevelopmentEvaluation:
    frames:tuple[ModuleFrameEvaluation,...]
    @property
    def processed(self):return len(self.frames)
    @property
    def confirmed_total(self):return sum(f.confirmed for f in self.frames)
    @property
    def failure_frames(self):return tuple(f.frame_id for f in self.frames if f.status!="confirmed")
