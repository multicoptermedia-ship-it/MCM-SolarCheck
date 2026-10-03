"""Cross-frame consistency checks for confirmed PV module observations."""
from __future__ import annotations
from dataclasses import dataclass
from statistics import median
from mcm_solarcheck.vision.module_identity import ModuleObservation

@dataclass(frozen=True)
class ModuleConsistency:
    accepted:bool
    reason:str

def assess_observation_geometry(observations:tuple[ModuleObservation,...],*,maximum_size_ratio:float=2.0)->ModuleConsistency:
    if not observations:return ModuleConsistency(False,"no_observations")
    sizes=[o.width*o.height for o in observations if o.width>0 and o.height>0]
    if len(sizes)!=len(observations):return ModuleConsistency(False,"invalid_size")
    m=median(sizes)
    if any(max(s/m,m/s)>maximum_size_ratio for s in sizes):return ModuleConsistency(False,"inconsistent_size")
    return ModuleConsistency(True,"accepted")
