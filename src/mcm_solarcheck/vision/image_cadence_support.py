"""Independent module-size intervals derived from image detector geometry."""
from __future__ import annotations
from mcm_solarcheck.vision.detection import ModuleDetection

def image_module_intervals(detections:tuple[ModuleDetection,...],axis_angle_deg:float)->tuple[float,...]:
    """Project each independent image detection onto a requested grid axis.

    The returned spans are evidence only; they neither create grid lines nor modules.
    """
    from math import cos,sin,radians
    if not detections:return ()
    u=(cos(radians(axis_angle_deg)),sin(radians(axis_angle_deg)));out=[]
    for d in detections:
        if len(d.polygon_px)<3:continue
        values=[x*u[0]+y*u[1] for x,y in d.polygon_px]
        span=max(values)-min(values)
        if span>1e-9:out.append(float(span))
    return tuple(out)
