"""Evidence-image planning for reviewed inspection findings.

This layer records which source images and pixel locations belong to report
evidence. Rendering/cropping is deliberately separate so original imagery stays
immutable and no RGB/Thermal coordinate equivalence is invented.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class EvidenceImagePlan:
    finding_id:str
    thermal_source:Path
    thermal_pixel:tuple[int,int]
    rgb_source:Path|None=None
    rgb_marker:tuple[float,float]|None=None
    pairing_confidence:float|None=None
    pairing_method:str|None=None
    def __post_init__(self):
        x,y=self.thermal_pixel
        if x<0 or y<0: raise ValueError('thermal pixel must be non-negative')
        if self.rgb_marker is not None and self.rgb_source is None: raise ValueError('RGB marker requires an RGB source image')
        if self.pairing_confidence is not None and not 0.0<=self.pairing_confidence<=1.0: raise ValueError('pairing confidence must be between 0 and 1')

@dataclass(frozen=True)
class EvidenceImageSet:
    plans:tuple[EvidenceImagePlan,...]


def plan_evidence_images(*,finding_id:str,thermal_source:str|Path,pixel_x:int,pixel_y:int,rgb_source:str|Path|None=None,pairing_confidence:float|None=None,pairing_method:str|None=None)->EvidenceImagePlan:
    """Create an immutable evidence plan without guessing RGB pixel coordinates."""
    return EvidenceImagePlan(finding_id=finding_id,thermal_source=Path(thermal_source),thermal_pixel=(pixel_x,pixel_y),rgb_source=Path(rgb_source) if rgb_source else None,rgb_marker=None,pairing_confidence=pairing_confidence,pairing_method=pairing_method)
