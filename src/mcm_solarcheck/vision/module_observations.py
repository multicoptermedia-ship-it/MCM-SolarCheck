"""Stable conversion from confirmed PV modules to physical identity observations."""
from __future__ import annotations
from mcm_solarcheck.vision.module_identity import ModuleObservation

def module_observations(modules)->tuple[ModuleObservation,...]:
    out=[]
    for m in modules:
        p=m.polygon_px;xs=[x for x,y in p];ys=[y for x,y in p]
        out.append(ModuleObservation(m.frame_id,m.module_id,(sum(xs)/len(xs),sum(ys)/len(ys)),max(xs)-min(xs),max(ys)-min(ys)))
    return tuple(out)
