"""Execution boundary for PV-module detectors on imported RGB frames."""
from __future__ import annotations
from dataclasses import dataclass
from mcm_solarcheck.domain.models import ImageFrame,PVModule
from mcm_solarcheck.vision.detection import ModuleDetection,normalize_module_detections

@dataclass(frozen=True)
class ModuleDetectionRun:
    frame_id:str
    modules:tuple[PVModule,...]
    detector_name:str
    status:str

class RawModuleDetector:
    @property
    def name(self)->str: ...
    def detect(self,source_file)->tuple[ModuleDetection,...]: ...

def detect_modules_in_frame(frame:ImageFrame,detector:RawModuleDetector,*,minimum_confidence:float=.50)->ModuleDetectionRun:
    """Run detector and normalize output only when frame geometry is known."""
    if frame.width is None or frame.height is None or frame.width<=0 or frame.height<=0:
        return ModuleDetectionRun(frame.frame_id,(),detector.name,"missing_image_geometry")
    detections=tuple(detector.detect(frame.source_file))
    modules=normalize_module_detections(frame.frame_id,detections,detector_name=detector.name,minimum_confidence=minimum_confidence,image_size=(frame.width,frame.height))
    return ModuleDetectionRun(frame.frame_id,modules,detector.name,"detected" if modules else "no_modules")
