"""Conservative fusion of independent PV-module detector evidence."""
from __future__ import annotations
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.polygon_geometry import convex_polygon_iou

def fuse_module_detections(primary:tuple[ModuleDetection,...],support:tuple[ModuleDetection,...],*,minimum_iou:float=.25,allow_primary_without_support:bool=False)->tuple[ModuleDetection,...]:
    """Keep primary grid cells only when independent image evidence overlaps them.

    No union is performed: support detections can confirm geometry but cannot create
    a physical module by themselves.
    """
    if not 0<=minimum_iou<=1:raise ValueError("minimum_iou must be between 0 and 1")
    if not support:return primary if allow_primary_without_support else ()
    out=[]
    for p in primary:
        overlaps=[( convex_polygon_iou(p.polygon_px,s.polygon_px),s) for s in support]
        best=max(overlaps,key=lambda x:x[0])
        if best[0]>=minimum_iou:
            confidence=min(.99,max(p.confidence,best[1].confidence)+.05)
            out.append(ModuleDetection(p.polygon_px,confidence,p.class_name))
    return tuple(out)
